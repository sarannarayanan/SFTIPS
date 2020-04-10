import os
from bson.json_util import dumps
from pymongo import MongoClient, UpdateOne, errors


class DatabaseConnector:
    """ Handle requests to Mongo DB"""

    def __init__(self, db_name):
        self.db_client = MongoClient(os.environ['MONGO_URI'], retryWrites=False)
        self.db_name = db_name

    def get_db(self):
        return self.db_client[self.db_name]

    def get_collection(self, collection):
        return self.get_db()[collection]

    @staticmethod
    def get_document_id_list(id_attribute, document_list):
        """ get a list of 'ids' given a set of records"""
        return [doc.get(id_attribute) for doc in document_list if doc.get(id_attribute)]

    def upsert_documents(self, collection, id_attribute, document_list):
        """ find matching records to update, if no matches are found, then insert new ones"""

        upserts = [UpdateOne({id_attribute: doc_id}, {'$set': doc}, upsert=True)
                   for doc_id, doc in zip(self.get_document_id_list(id_attribute, document_list),
                                          document_list)]
        try:
            result = self.get_collection(collection).bulk_write(upserts)
            return dumps(result.bulk_api_result)
        except errors.PyMongoError as error:
            return dumps(str(error))

    def get_random_documents(self, collection, size=1):
        results = self.get_collection(collection).aggregate([{"$sample": {"size":size} } ])
        documents = []
        for count, document in enumerate(results):
            documents.append(document)
            if count == size:
                break
        return documents