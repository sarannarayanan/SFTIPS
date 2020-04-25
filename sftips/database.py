from google.cloud import firestore

import random


class DatabaseError(Exception):
    pass


class DatabaseConnector:
    """ Handle requests to Firestore DB"""

    _client = None

    def __init__(self):
        self.client = self.get_client()

    def get_client(self):
        # for local dev, GOOGLE_APPLICATION_CREDENTIALS env var must be set
        if self._client:
            return self._client
        else:
            self._client = firestore.Client()

    def get_all_documents(self, collection):
        document_list = self.get_client().collection(collection)
        documents = [doc.to_dict() for doc in document_list.stream()]
        return documents

    def upsert_batch(self, collection, documents, key_attribute):
        "collection name, list of dicts, and field to match, returns None"
        try:

            batch = self.get_client().batch()

            for document in documents:
                document['timestamp'] = firestore.SERVER_TIMESTAMP
                doc_ref = self.get_client().collection(collection).document(document[key_attribute])
                batch.set(doc_ref, document)
            return batch.commit() is not None
        except Exception as error:
            raise DatabaseError(str(error))

    def get_document(self, collection, document_id):
        doc_ref = self.get_client().collection(collection).document(document_id)
        doc = doc_ref.get()
        if doc.exists:
            return doc.to_dict()

    def get_random_document(self, collection):
        all_docs = self.get_all_documents(collection)
        return random.choice(all_docs)