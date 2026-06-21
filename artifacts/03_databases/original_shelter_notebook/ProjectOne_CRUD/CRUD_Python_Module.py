from pymongo import MongoClient
from bson.objectid import ObjectId

class AnimalShelter(object):
    """ CRUD operations for Animal collection in MongoDB """

    def __init__(self, username, password):
        """
        Initialize connection to MongoDB with authentication.

        Args:
            username (str): MongoDB username for authentication
            password (str): MongoDB password for authentication
        """
        # Connection variables
        HOST = 'localhost'
        PORT = 27017
        DB = 'aac'
        COL = 'animals'

        # Initialize connection with authentication
        self.client = MongoClient('mongodb://%s:%s@%s:%d' % (username, password, HOST, PORT))
        self.database = self.client['%s' % (DB)]
        self.collection = self.database['%s' % (COL)]

    # Method to implement C in CRUD - Create
    def create(self, data):
        """
        Insert a new document into the animals collection.

        Args:
            data (dict): Key-value pairs representing the document to insert

        Returns:
            bool: True if successful, False otherwise

        Raises:
            Exception: If data parameter is None or empty
        """
        if data is not None:
            # data should be a dictionary, insert into collection
            try:
                self.collection.insert_one(data)
                return True
            except Exception as e:
                # Return False if insert fails for any reason
                return False
        else:
            raise Exception("Nothing to save, because data parameter is empty")

    # Method to implement R in CRUD - Read
    def read(self, data):
        """
        Query documents from the animals collection.

        Args:
            data (dict): Key-value lookup pairs for the MongoDB find query

        Returns:
            list: Matching documents as a Python list, or empty list if no match
        """
        if data is not None:
            # find() returns a cursor, convert to list for easy iteration
            result = list(self.collection.find(data))
            return result
        else:
            # return empty list if no query provided
            return []

    # Method to implement U in CRUD - Update
    def update(self, lookup, updateData):
        """
        Update documents in the animals collection matching the lookup criteria.

        Args:
            lookup (dict): Key-value pairs to identify documents to update
            updateData (dict): Key-value pairs with the new field values

        Returns:
            int: Number of documents modified

        Raises:
            Exception: If lookup parameter is None or empty
        """
        if lookup is not None:
            # Use $set to update only specified fields, leaving others unchanged
            result = self.collection.update_many(lookup, {"$set": updateData})
            return result.modified_count
        else:
            raise Exception("Nothing to update, because lookup parameter is empty")

    # Method to implement D in CRUD - Delete
    def delete(self, data):
        """
        Remove documents from the animals collection matching the query.

        Args:
            data (dict): Key-value pairs to identify documents to delete

        Returns:
            int: Number of documents deleted

        Raises:
            Exception: If data parameter is None or empty
        """
        if data is not None:
            # Delete all documents matching the query criteria
            result = self.collection.delete_many(data)
            return result.deleted_count
        else:
            raise Exception("Nothing to delete, because data parameter is empty")
