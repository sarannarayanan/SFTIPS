import json
import logging
import os
import pathlib
import random
import re
import yaml
from abc import ABC, abstractmethod

import falcon
from bson.json_util import loads, dumps
from pydialogflow_fulfillment import DialogflowResponse, SimpleResponse

from sftips.database import DatabaseConnector

LOGGER = logging.getLogger(__name__)
LOGGER.addHandler(logging.StreamHandler())
LOGGER.setLevel(logging.DEBUG)
TIP_SERVICE = TIP_APP = falcon.API()
TIP_ROUTE = '/tips'
TIP_REQUEST_ROUTE = '/tip-request'
GOOGLE_TIP_REQUEST_ROUTE = '/google-tip-request'
ROOT = '/'
DB = DatabaseConnector(os.environ['DB_NAME'])


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

    @staticmethod
    def get_random_message(message_type):
        msg_file = pathlib.Path(__file__).parent.parent / 'resources/messages.yaml'
        with open(msg_file) as file:
            messages = yaml.load(file, Loader=yaml.FullLoader)
            return random.choice(messages[message_type])


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
            results = DB.upsert_documents('tips', 'sfdc_id', tips['tips'])
            db_results = loads(results)
            if type(db_results) is dict and db_results.get('nModified') == 0 and \
                    db_results.get('nMatched') > 0 and db_results.get('nUpserted') == 0:
                LOGGER.info('Records were matched but none were modified. {}'.format(db_results))
                resp.status = falcon.HTTP_200
                resp.body = self.generate_json_response(db_results)
            elif type(db_results) is dict and \
                    (db_results.get('nModified') > 0 or db_results.get('nUpserted') > 0):
                LOGGER.info('Records were modified or upserted. {}'.format(db_results))
                resp.status = falcon.HTTP_201
                resp.body = self.generate_json_response(db_results)
            else:
                LOGGER.error('There was a problem processing the request')
                raise Exception(db_results)
        except Exception as ex:
            raise falcon.HTTPError(falcon.HTTP_400, 'Error Processing Tip. Error: ', str(ex))


class TipRequest(BaseRequest):

    def __init__(self):
        self.tip = dict()
        self.message = str()
        self.response = None

    def get_tip(self):
        LOGGER.info('Received request to retrieve tip.')
        results = DB.get_random_documents('tips', size=1)  # just get one
        if results:
            LOGGER.info('Document retrieved successfully')
            self.tip = results[0]

    def get_ssml_message(self):
        return self.message

    def get_text_message(self):
        return re.sub('<[^>]+>', '', self.message)

    def build_message(self):
        LOGGER.info('Building message')
        self.message = "<speak>"
        self.message += self.get_random_message('welcome')  # 'Hi!'
        self.message += self.insert_paragraph(self.tip['title'])  # 'Considering enabling SSO in your org."
        self.add_speech_pause('2s')
        self.message += self.insert_paragraph(self.tip['content'])  # SSO is good for your soul
        self.add_speech_pause('3s')
        self.message += self.insert_paragraph(self.get_random_message('goodbye'))  # 'goodbye!'
        self.message += "</speak>"

    def add_speech_pause(self, time):
        # use SSML syntax to define time, i.e 1s or 500ms
        self.message += '<break time=\"' + time + '\"/>'

    @staticmethod
    def insert_paragraph(text):
        return ' \n\n <p>' + text + '</p> \n\n'

    def process_request(self):
        self.get_tip()
        self.build_message()

    @abstractmethod
    def get_platform_response(self):
        pass

    def answer(self, resp):
        LOGGER.info('Preparing and sending HTTP Response')
        resp.status = falcon.HTTP_200
        resp.body = self.get_platform_response()
        resp.content_type = falcon.MEDIA_JSON

    @staticmethod
    def get_random_message(message_type):
        msg_file = pathlib.Path(__file__).parent / 'resources/messages.yaml'
        with open(msg_file) as file:
            messages = yaml.load(file, Loader=yaml.FullLoader)
            return random.choice(messages[message_type])


class GoogleTipRequest(TipRequest):

    def __init__(self):
        super().__init__()

    def on_post(self, req, resp):
        self.process_request()
        self.answer(resp)

    def get_platform_response(self):
        dialogflow_response = DialogflowResponse()
        dialogflow_response.expect_user_response = False
        dialogflow_response.add(SimpleResponse(self.get_text_message(), self.get_ssml_message()))
        return dialogflow_response.get_final_response()


TIP_APP.add_route(ROOT, RootRequest())
TIP_APP.add_route(TIP_ROUTE, Tip())
TIP_APP.add_route(GOOGLE_TIP_REQUEST_ROUTE, GoogleTipRequest())
