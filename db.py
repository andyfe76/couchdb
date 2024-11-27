import requests
import json
import logging
from typing import Generator

# Configure the logger
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class Db():
    def __init__(self, host: str, port: int, database: str, username: str, password: str) -> None:
        '''
        host: str: Hostname of the CouchDB server
        port: int: Port number of the CouchDB server
        database: str: Name of the database
        username: str: Username for the CouchDB server
        password: str: Password for the CouchDB server
        '''
        self.session = requests.Session()
        self.session.headers.update({'Content-Type': 'application/json'})
        self.session.auth = (username, password)

        self._url = f"{host}:{port}/{database}"
        
        logger.info(f"Connected to CouchDB at {self._url}")

    def get(self, id: str) -> dict:
        '''
        id: str: Document ID
        
        Returns the document with the given ID
        '''
        res = self.session.get(f"{self._url}/{id}")
        if res.status_code != 200:
            return None
        
        return res.json()
    
    def post(self, doc: dict) -> dict:
        '''
        doc: dict: Document to be inserted
        
        Inserts the given document into the database. Uses the CouchDB uuid to generate the _id
        
        Returns the inserted document with the _id and _rev
        '''
        res = self.session.post(f"{self._url}", json=doc)
        if res.status_code != 201:
            return None
        
        res = res.json()
        doc['_id'], doc['_rev'] = res['id'], res['rev']
        return doc
    
    def put(self, doc: dict) -> dict:
        '''
        doc: dict: Document to be updated
        
        Updates the given document in the database
        
        Returns the updated document with the new _rev
        '''

        # If the document does not have an _id, insert it
        if doc.get('_id', None) is None:
            return self.post(doc)
        
        # If the document has a _rev and is None, remove it (for ORM integration)
        if '_rev' in doc and doc['_rev'] is None:
            doc.pop('_rev', None)
        
        result = self.session.put(f"{self._url}/{doc['_id']}", json=doc)
        if result.status_code not in [200, 201]:
            # If there is a document conflict, get the current document and update it
            current_doc = self.get(doc['_id'])
            if current_doc:
                current_doc.update(doc)
                result = self.session.put(f"{self._url}/{current_doc['_id']}", json=current_doc)
            else:
                return None
        
        res = result.json()
        doc['_rev'] = res['rev']
        return doc
    
    def bulk_update(self, docs: list) -> list:
        '''
        docs: list: List of documents to be updated
        
        Updates the given documents in the database
        
        Returns the updated documents with the new _rev
        '''
        # Remove the _rev field if it is empty (first time insert)
        [doc.pop('_rev', None) for doc in docs if not doc.get('_rev', None)]

        result = self.session.post(f"{self._url}/_bulk_docs", json={"docs": docs}).json()
        # update id and rev to _id and _rev for all docs
        [doc.update({'_id': result[i]['id'], '_rev': result[i]['rev']}) for i, doc in enumerate(docs)]
        return docs
    
    def delete(self, doc: dict) -> dict:
        '''
        doc: dict: Document to be deleted
        
        Deletes the given document from the database

        Returns the deleted document with the _deleted field set to True
        '''
        doc['_deleted'] = True
        return self.put(doc)

    def find(self, query: dict={}, skip:int = 0, limit: int = 50000, fields: list = None) -> list:
        '''
        query: dict: Query selector
        skip: int: Number of documents to skip
        limit: int: Number of documents to return
        fields: list: List of fields to return
        
        Returns the documents that match the given query
        '''
        # Pass the selector and other parameters separately
        selector = {"selector": query}
        
        selector['skip'] = skip
        selector['limit'] = limit
        if fields: 
            selector['fields'] = fields

        result = self.session.post(f"{self._url}/_find", json=selector)
        if result.status_code != 200:
            return []
        return result.json().get('docs', [])
        
    
    def find_first(self, query: dict = {}, skip: int  = 0, fields: list = None):
        '''
        query: dict: Query selector
        skip: int: Number of documents to skip
        fields: list: List of fields to return
        '''
        result = self.find(query=query, skip=skip, limit=1, fields=fields)
        if len(result) > 0:
            return result[0]
        else:
            return None
        
    def set_rev_limit(self, limit: int) -> dict:
        '''
        limit: int: Number of revisions to keep for each document
        '''
        return self.session.put(f"{self._url}/_revs_limit", json=limit).json()

    def compact(self):
        '''
        Compacts the database
        '''
        return self.session.post(f"{self._url}/_compact").json()

    def cleanup(self):
        '''
        Cleans up the database
        '''
        return self.session.post(f"{self._url}/_view_cleanup").json()
    
    def deleted_docs(self) -> dict:
        '''
        Returns a dictionary of deleted document ids as keys and and their revisions as values
        '''
        result = self.session.post(f"{self._url}/_changes", params={'include_docs': "true"}, data=json.dumps({}).encode("utf-8"), json=True)
        if result.status_code != 200:
            return []
        
        deleted_docs = {}
        for item in result.json()['results']:
            doc = item.get('doc', None)
            if doc and doc.get("_deleted", False):
                if not deleted_docs.get(doc['_id'], None):
                    deleted_docs[doc['_id']] = []
                deleted_docs[doc['_id']].append(doc['_rev'])
        return deleted_docs
    

    def purge(self, data: dict) -> dict:
        '''
        Permanently removes the documents revisions in the database

        data: dict: Dictionary of document ids as keys and their revisions as values
        '''
        return self.session.post(f"{self._url}/_purge", json=data).json()

    def purge_all(self) -> dict:
        '''
        Purge all revisions for all deleted documents
        '''
        return self.purge(self.deleted_docs())
    

    def changes(self, query: dict = None) -> Generator[dict, None, None]:
        '''
        query: dict: Query selector

        Returns a generator that yields the changes in the database
        '''
        params = {"feed":"longpoll", "since":"now", "include_docs": "true", "live": "true"}
        data = {}
        if query:
            params['filter']  = '_selector'
            data['selector'] = query
            
        while True:
            response = self.session.post(f"{self._url}/_changes", params=params, json=data, stream=True)
            try:
                for res in response.json()['results']:
                    yield res['doc']
            except Exception as e:
                logger.error(f"Error: {e}")
                break
    
    def close(self):
        '''
        Closes the connection to the database
        '''
        self.session.close()