import json
import logging
import random

from falcon import API, MEDIA_JSON, HTTP_200
import requests

LOGGER = logging.getLogger(__name__)
LOGGER.addHandler(logging.StreamHandler())
LOGGER.setLevel(logging.DEBUG)
TIP_SERVICE_API = TIP_APP = API()
TIP_ROUTE = '/tip'


class APIException(Exception):
    """ Generic Exception for this API"""


class TipRequest():
    """Represents a request to TIP API endpoint"""

    def on_post(self, req, resp):
        """Handles POST requests"""
        pass
