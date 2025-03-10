import os
from dotenv import load_dotenv
import logging
from pymongo import MongoClient

logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

class DatabaseClient:
    """Database client for MongoDB connection and collections."""
    
    def __init__(self):
        """Initialize with MongoDB connection."""
        mongo_uri = os.getenv("MONGO_URI", "mongodb://localhost:27017")
        db_name = os.getenv("MONGO_DB_NAME", "fusevault")
        
        try:
            self.client = MongoClient(mongo_uri)
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
            raise
    
    def close(self):
        """Close the MongoDB connection."""
        if hasattr(self, 'client'):
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
