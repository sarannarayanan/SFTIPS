import json
import logging
import os
from bson.json_util import loads, dumps

from sftips.database import DatabaseConnector

import falcon
LOGGER = logging.getLogger(__name__)
LOGGER.addHandler(logging.StreamHandler())
LOGGER.setLevel(logging.DEBUG)
TIP_SERVICE = TIP_APP = falcon.API()
TIP_ROUTE = '/tips'
ROOT = '/'
DB = DatabaseConnector(os.environ['DB_NAME'])


class APIException(Exception):
    """ Generic Exception for this API"""


class BaseRequest():
    """Represents a request to ROOT API endpoint"""

    def on_get(self, req, resp):
        data = {'status': 'Always look at the bright side of life!'}
        resp.status = falcon.HTTP_200
        resp.body = json.dumps(data, sort_keys=True, indent=2, separators=(',', ': '))


class Tip():
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

    @staticmethod
    def generate_json_response(data):
        return dumps(data)


TIP_APP.add_route(ROOT, BaseRequest())
TIP_APP.add_route(TIP_ROUTE, Tip())



