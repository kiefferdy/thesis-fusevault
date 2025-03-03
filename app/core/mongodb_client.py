import os
import logging
from typing import Dict, Any, Optional, List
from datetime import datetime, timezone
from uuid import uuid4
from pymongo import MongoClient, DESCENDING
from bson import ObjectId
from dotenv import load_dotenv

# Set up logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

class MongoDBClient:
    _instance = None
    _initialized = False

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(MongoDBClient, cls).__new__(cls)
        return cls._instance

    def __init__(self):
        if self._initialized:
            return

        # Load environment variables
        load_dotenv()
        
        # Get MongoDB URI from environment
        self.mongo_uri = os.getenv("MONGO_URI")
        if not self.mongo_uri:
            raise ValueError("MONGO_URI environment variable is not set")

        try:
            # Initialize MongoDB connection
            self.client = MongoClient(self.mongo_uri)
            
            # Initialize database and collections
            self.db = self.client.get_database("fusevault")
            self.assets_collection = self.db["assets"]
            self.users_collection = self.db["users"]
            self.transaction_collection = self.db["transactions"]
            self.sessions_collection = self.db["sessions"]
            
            # 🔥 Add auth_collection for MetaMask authentication
            self.auth_collection = self.db["auth"]

            # Create indexes
            self._create_indexes()
            
            self._initialized = True
            logger.info("Successfully connected to MongoDB")
            
        except Exception as e:
            logger.error(f"Failed to connect to MongoDB: {str(e)}")
            raise ConnectionError(f"Failed to connect to MongoDB: {str(e)}")

        try:
            collections = self.db.list_collection_names()
            logger.info(f"Available collections: {collections}")

            # Ensure auth collection exists
            if "auth" not in collections:
                logger.warning("Auth collection not found, creating it...")
                self.db.create_collection("auth")
                
            # Log auth collection info
            logger.info(f"Auth collection info: {self.auth_collection.find_one()}")

        except Exception as e:
            logger.error(f"Error verifying collections: {str(e)}")

    def _create_indexes(self):
        """Create necessary indexes for collections"""
        try:
            # Indexes for documents
            self.assets_collection.create_index([("walletAddress", 1)])
            self.assets_collection.create_index([("ipfsHash", 1)])
            self.assets_collection.create_index([("smartContractTxId", 1)])

            # 🔥 Index for authentication (walletAddress lookup)
            self.auth_collection.create_index([("walletAddress", 1)], unique=True)

        except Exception as e:
            logger.error(f"Failed to create indexes: {str(e)}")
            raise

    # 🔥 Authentication Methods for MetaMask Login
    def get_nonce(self, wallet_address: str) -> Optional[int]:
        """Retrieve nonce for a given wallet address or create a new one."""
        try:
            user_auth = self.auth_collection.find_one({"walletAddress": wallet_address})
            if user_auth and "nonce" in user_auth:
                return user_auth["nonce"]
            return self.generate_nonce(wallet_address)
        except Exception as e:
            logger.error(f"Error retrieving nonce: {str(e)}")
            raise

    def generate_nonce(self, wallet_address: str) -> int:
        """Generate and store a new nonce for authentication."""
        nonce = int(uuid4().int % 1000000)  # Generate a random 6-digit nonce
        self.auth_collection.update_one(
            {"walletAddress": wallet_address},
            {"$set": {"nonce": nonce}},
            upsert=True
        )
        return nonce

    def update_nonce(self, wallet_address: str):
        """Generate a new nonce after successful authentication."""
        new_nonce = int(uuid4().int % 1000000)
        self.auth_collection.update_one(
            {"walletAddress": wallet_address},
            {"$set": {"nonce": new_nonce}}
        )

    def close_connection(self):
        """Close the MongoDB connection"""
        if hasattr(self, 'client'):
            self.client.close()
            logger.info("MongoDB connection closed")
