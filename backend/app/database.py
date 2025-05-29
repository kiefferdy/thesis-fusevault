import logging
from typing import Dict, Any, List, Optional
import json
from datetime import datetime, timezone
from bson import ObjectId
import traceback

from app.config import settings

# Try to import pymongo, but fall back to a mock implementation if not available
try:
    from pymongo import MongoClient
    MONGODB_AVAILABLE = True
except ImportError:
    MONGODB_AVAILABLE = False
    logging.warning("pymongo not available, using mock database for development")

logger = logging.getLogger(__name__)

# Helper to convert ObjectId to string in JSON serialization
class JSONEncoder(json.JSONEncoder):
    def default(self, o):
        if isinstance(o, ObjectId):
            return str(o)
        if isinstance(o, datetime):
            return o.isoformat()
        return json.JSONEncoder.default(self, o)

# Mock collection for development
class MockCollection:
    def __init__(self, name: str):
        self.name = name
        self.data = []
        self.id_counter = 1000  # Start with a high number to avoid conflicts
        logger.info(f"Created mock collection: {name}")
    
    def find_one(self, query: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Simple query matching implementation"""
        for item in self.data:
            matches = True
            for key, value in query.items():
                if key not in item:
                    matches = False
                    break
                
                # Handle special $gt operator
                if isinstance(value, dict) and "$gt" in value:
                    if not (item[key] > value["$gt"]):
                        matches = False
                        break
                # Handle normal equality
                elif item[key] != value:
                    matches = False
                    break
            
            if matches:
                return json.loads(json.dumps(item, cls=JSONEncoder))
        
        return None
    
    def find(self, query: Dict[str, Any] = None) -> List[Dict[str, Any]]:
        """Simple find implementation"""
        if query is None:
            query = {}
        
        results = []
        for item in self.data:
            matches = True
            for key, value in query.items():
                if key not in item:
                    matches = False
                    break
                
                # Handle special $gt operator
                if isinstance(value, dict) and "$gt" in value:
                    if not (item[key] > value["$gt"]):
                        matches = False
                        break
                # Handle normal equality
                elif item[key] != value:
                    matches = False
                    break
            
            if matches:
                results.append(json.loads(json.dumps(item, cls=JSONEncoder)))
        
        return results
    
    def insert_one(self, document: Dict[str, Any]) -> Any:
        """Insert a document"""
        document = json.loads(json.dumps(document, cls=JSONEncoder))
        
        if "_id" not in document:
            document["_id"] = ObjectId()
        
        self.data.append(document)
        
        class Result:
            @property
            def inserted_id(self):
                return document["_id"]
        
        return Result()
    
    def update_one(self, query: Dict[str, Any], update: Dict[str, Any], upsert: bool = False) -> Any:
        """Update a document"""
        item = self.find_one(query)
        
        if item is None:
            if upsert:
                # Create a new document
                document = {}
                for key, value in query.items():
                    document[key] = value
                
                if "$set" in update:
                    for key, value in update["$set"].items():
                        document[key] = value
                
                self.insert_one(document)
                
                class Result:
                    @property
                    def modified_count(self):
                        return 0
                    
                    @property
                    def upserted_id(self):
                        return document["_id"]
                
                return Result()
            else:
                class Result:
                    @property
                    def modified_count(self):
                        return 0
                    
                    @property
                    def upserted_id(self):
                        return None
                
                return Result()
        
        # Apply updates
        for i, doc in enumerate(self.data):
            if doc.get("_id") == item.get("_id"):
                if "$set" in update:
                    for key, value in update["$set"].items():
                        self.data[i][key] = value
                break
        
        class Result:
            @property
            def modified_count(self):
                return 1
            
            @property
            def upserted_id(self):
                return None
        
        return Result()
    
    def delete_one(self, query: Dict[str, Any]) -> Any:
        """Delete a document"""
        item = self.find_one(query)
        
        if item is None:
            class Result:
                @property
                def deleted_count(self):
                    return 0
            
            return Result()
        
        # Delete item
        for i, doc in enumerate(self.data):
            if doc.get("_id") == item.get("_id"):
                del self.data[i]
                break
        
        class Result:
            @property
            def deleted_count(self):
                return 1
        
        return Result()
    
    def update_many(self, query: Dict[str, Any], update: Dict[str, Any]) -> Any:
        """Update multiple documents"""
        items = self.find(query)
        count = 0
        
        for item in items:
            for i, doc in enumerate(self.data):
                if doc.get("_id") == item.get("_id"):
                    if "$set" in update:
                        for key, value in update["$set"].items():
                            self.data[i][key] = value
                    count += 1
                    break
        
        class Result:
            @property
            def modified_count(self):
                return count
        
        return Result()

class DatabaseClient:
    """Database client for MongoDB connection and collections."""
    
    def __init__(self):
        """Initialize with MongoDB connection or mock implementation."""
        self.using_mock = False
        
        if MONGODB_AVAILABLE:
            mongo_uri = settings.mongo_uri
            db_name = settings.mongo_db_name
            
            try:
                self.client = MongoClient(mongo_uri, serverSelectionTimeoutMS=5000)
                # Test connection
                self.client.admin.command('ping')
                self.db = self.client[db_name]
                
                # Initialize collections
                self.assets_collection = self.db["assets"]
                self.auth_collection = self.db["auth"]
                self.sessions_collection = self.db["sessions"]
                self.transaction_collection = self.db["transactions"]
                self.users_collection = self.db["users"]
                
                logger.info(f"Connected to MongoDB database: {db_name}")
                
            except Exception as e:
                logger.error(f"Error connecting to MongoDB: {str(e)}")
                logger.error(traceback.format_exc())
                self._setup_mock_collections()
        else:
            self._setup_mock_collections()
    
    def _setup_mock_collections(self):
        """Set up mock collections for development"""
        self.using_mock = True
        
        # Create mock collections
        self.assets_collection = MockCollection("assets")
        self.auth_collection = MockCollection("auth")
        self.sessions_collection = MockCollection("sessions")
        self.transaction_collection = MockCollection("transactions")
        self.users_collection = MockCollection("users")
        
        logger.warning("Using mock database for development")
        
        # Add some sample data
        self.users_collection.insert_one({
            "walletAddress": "0x1234567890123456789012345678901234567890",
            "email": "demo@example.com",
            "role": "admin",
            "createdAt": datetime.now(timezone.utc),
            "lastLogin": datetime.now(timezone.utc)
        })
    
    def get_collection(self, collection_name: str):
        """
        Get a collection by name.
        
        Args:
            collection_name: Name of the collection
            
        Returns:
            Collection object
        """
        if self.using_mock:
            # For mock, create a new collection if it doesn't exist
            if not hasattr(self, f"{collection_name}_collection"):
                setattr(self, f"{collection_name}_collection", MockCollection(collection_name))
            return getattr(self, f"{collection_name}_collection")
        else:
            return self.db[collection_name]
    
    def close(self):
        """Close the MongoDB connection."""
        if not self.using_mock and hasattr(self, 'client'):
            self.client.close()
            logger.info("MongoDB connection closed")

# Create a singleton instance
db_client = None

def get_db_client() -> DatabaseClient:
    """
    Get the database client instance.
    
    Returns:
        DatabaseClient instance
    """
    global db_client
    
    if db_client is None:
        db_client = DatabaseClient()
        
    return db_client