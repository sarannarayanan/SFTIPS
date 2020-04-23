import json
import logging
import pathlib
import random
import re
import yaml
from abc import ABC, abstractmethod
from collections import namedtuple

from . import messages as msgs

import falcon
from bson.json_util import loads, dumps
from pydialogflow_fulfillment import DialogflowResponse, SimpleResponse

from sftips.database import DatabaseConnector

FORMATTER = logging.Formatter('%(name)s - %(message)s')
HANDLER = logging.StreamHandler()
HANDLER.setFormatter(FORMATTER)
LOGGER = logging.getLogger(__name__)
LOGGER.setLevel(logging.DEBUG)
LOGGER.addHandler(HANDLER)

TIP_SERVICE = TIP_APP = falcon.API()
TIP_ROUTE = '/tips'
TIP_REQUEST_ROUTE = '/tip-request'
GOOGLE_TIP_REQUEST_ROUTE = '/google-tip-request'
AMAZON_TIP_REQUEST_ROUTE = '/amazon-tip-request'
ROOT = '/'
DB = DatabaseConnector()


class APIException(Exception):
    """ Generic Exception for this API"""


class BaseRequest(ABC):
    """Represents a request to ROOT API endpoint"""

    def on_get(self, req, resp):
        data = {'status': 'Always look at the bright side of life!'}
        resp.status = falcon.HTTP_200
        resp.body = json.dumps(data, sort_keys=True, indent=2, separators=(',', ': '))

    @staticmethod
    def generate_json_response(data):
        return dumps(data)

    @abstractmethod
    def on_post(self, req, resp):
        pass


class RootRequest(BaseRequest):

    def on_get(self, req, resp):
        super().on_get(req, resp)

    def on_post(self):
        pass


class Tip(BaseRequest):
    """ Serves requests to TIP API endpoint"""

    def on_post(self, req, resp):
        """Handles POST requests that deal with the creation of tips"""

        try:
            tips = json.load(req.bounded_stream)
            LOGGER.info('Received tip creation request. Proceeding to upsert')
            results = DB.upsert_batch('tips', tips['tips'], 'sfdc_id', )
            if results:
                LOGGER.info('Records were upserted. {}'.format(results))
                resp.status = falcon.HTTP_201
                resp.body = self.generate_json_response(results)
            else:
                resp.status = 200
                resp.body = self.generate_json_response('Nothing to create.')
        except Exception as ex:
            raise falcon.HTTPError(falcon.HTTP_500, 'Error Processing Tip. Error: ', str(ex))


class TipRequest(BaseRequest):

    def __init__(self):
        self.random_tip = dict()
        self.tips = list()
        self.message = str()
        self.response = None

    @abstractmethod
    def get_platform_response(self):
        pass

    def create_message(self):
        self.message = msgs.get_greeting() + '\n'  # Welcome to ...
        self.message += self.random_tip.title + '\n'  # Use a single trigger per object
        self.message += self.random_tip.content + '\n'  # it is good for the ozone layer
        self.message += msgs.get_goodbye_message() + '\n'  # bye

    def answer(self, resp):
        LOGGER.info('Preparing and sending HTTP Response')
        resp.status = falcon.HTTP_200
        resp.body = self.get_platform_response()
        resp.content_type = falcon.MEDIA_JSON


class GoogleTipRequest(TipRequest):

    def __init__(self):
        super().__init__()

    def on_post(self, req, resp):
        self.request_tips()
        self.create_message()
        self.answer(resp)

    def request_tips(self):
        LOGGER.info('Received request to retrieve tip')
        results = DB.get_random_document('tips')
        if results:
            LOGGER.info('Document retrieved successfully')
            self.random_tip = namedtuple("Tip", results.keys())(*results.values())

    def get_platform_response(self):
        dialogflow_response = DialogflowResponse()
        dialogflow_response.expect_user_response = False
        dialogflow_response.add(SimpleResponse(self.message,
                                               msgs.text_to_ssml(self.message)))
        return dialogflow_response.get_final_response()


class AmazonTipRequest(TipRequest):

    def __init__(self):
        super().__init__()

    def on_post(self, req, resp):
        self.request_tips()
        self.create_message()
        self.answer(resp)

    def request_tips(self):
        # your logic to get tips here
        pass

    def get_platform_response(self):
        # your amazon platform response logic
        pass


TIP_APP.add_route(ROOT, RootRequest())
TIP_APP.add_route(TIP_ROUTE, Tip())
TIP_APP.add_route(GOOGLE_TIP_REQUEST_ROUTE, GoogleTipRequest())
TIP_APP.add_route(AMAZON_TIP_REQUEST_ROUTE, AmazonTipRequest())

