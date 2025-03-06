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

    def insert_document(self, asset_id: str, wallet_address: str,
                   smart_contract_tx_id: str, ipfs_hash: str,
                   critical_metadata: Dict[str, Any],
                   non_critical_metadata: Optional[Dict[str, Any]] = None) -> str:
        """Insert a new document into MongoDB"""
        try:
            # First verify user exists
            user = self.get_user_by_wallet(wallet_address)
            if not user:
                raise ValueError("User not found")

            document = {
                "assetId": asset_id,
                "versionNumber": 1,  # Explicitly set first version
                "walletAddress": wallet_address,
                "smartContractTxId": smart_contract_tx_id,
                "ipfsHash": ipfs_hash,
                "lastVerified": datetime.now(timezone.utc),
                "lastUpdated": datetime.now(timezone.utc),
                "criticalMetadata": critical_metadata,
                "nonCriticalMetadata": non_critical_metadata or {},
                "isCurrent": True,
                "isDeleted": False,
                "documentHistory": []
            }
            
            result = self.assets_collection.insert_one(document)
            doc_id = str(result.inserted_id)
            
            # Record transaction
            self.record_transaction(asset_id, "CREATE", wallet_address)
            
            return doc_id
            
        except Exception as e:
            logger.error(f"Error inserting document: {str(e)}")
            raise

    def get_document_by_id(self, asset_id: str, version_number: Optional[int] = None) -> Dict[str, Any]:
        """
        Retrieve a document by its Asset ID and optionally a specific version.
        If version_number is not provided, returns the current version.
        """
        try:
            # Set up the query
            query = {"assetId": asset_id}
            
            if version_number is not None:
                # Get specific version
                query["versionNumber"] = version_number
            else:
                # Get current version
                query["isCurrent"] = True
            
            document = self.assets_collection.find_one(query)
            
            if not document:
                if version_number:
                    raise ValueError(f"Document with Asset ID {asset_id} and version {version_number} not found")
                else:
                    raise ValueError(f"Document with Asset ID {asset_id} not found")
                
            # Convert MongoDB's ObjectId to string for the response
            document['_id'] = str(document['_id'])
            return document
        
        except Exception as e:
            logger.error(f"Error retrieving document: {str(e)}")
            raise

    def get_documents_by_wallet(self, wallet_address: str, include_all_versions: bool = False) -> List[Dict[str, Any]]:
        """
        Retrieve all documents for a wallet address.
        By default, only returns current versions unless include_all_versions is True.
        """
        try:
            query = {
                "walletAddress": wallet_address,
                "isDeleted": False
            }
            
            if not include_all_versions:
                query["isCurrent"] = True
                
            cursor = self.assets_collection.find(query)
            documents = list(cursor)
            
            # Convert ObjectId to string for each document
            for doc in documents:
                doc['_id'] = str(doc['_id'])
                
            return documents
        except Exception as e:
            logger.error(f"Error retrieving documents: {str(e)}")
            raise

    def update_document(self, asset_id: str, smart_contract_tx_id: str,
                   ipfs_hash: str, critical_metadata: Dict[str, Any],
                   non_critical_metadata: Optional[Dict[str, Any]] = None) -> bool:
        """Update the current version of a document"""
        try:
            # Get the current document
            current_doc = self.assets_collection.find_one({
                "assetId": asset_id,
                "isCurrent": True
            })
            
            if not current_doc:
                return False

            # Update the document
            update_result = self.assets_collection.update_one(
                {"_id": current_doc["_id"]},
                {
                    "$set": {
                        "smartContractTxId": smart_contract_tx_id,
                        "ipfsHash": ipfs_hash,
                        "criticalMetadata": critical_metadata,
                        "nonCriticalMetadata": non_critical_metadata or {},
                        "lastUpdated": datetime.now(timezone.utc)
                    }
                }
            )
            
            if update_result.modified_count > 0:
                # Record transaction
                self.record_transaction(asset_id, "UPDATE", current_doc["walletAddress"])
                return True
                
            return False
            
        except Exception as e:
            logger.error(f"Error updating document: {str(e)}")
            raise

    def create_new_version(self, asset_id: str, wallet_address: str,
                      smart_contract_tx_id: str, ipfs_hash: str,
                      critical_metadata: Dict[str, Any],
                      non_critical_metadata: Dict[str, Any] = None) -> str:
        """Create a new version of an existing document"""
        try:
            # Find the latest version
            latest_doc = self.assets_collection.find_one(
                {"assetId": asset_id, "isCurrent": True}
            )
            
            if not latest_doc:
                raise ValueError(f"Document with Asset ID {asset_id} not found")
                
            new_version_number = latest_doc.get("versionNumber", 1) + 1
            
            # Mark previous as not current FIRST
            self.assets_collection.update_one(
                {"_id": latest_doc["_id"]},
                {"$set": {"isCurrent": False}}
            )
            
            # Create new document
            new_doc = {
                "assetId": asset_id,
                "versionNumber": new_version_number,  # Make sure this is set!
                "walletAddress": wallet_address,
                "smartContractTxId": smart_contract_tx_id,
                "ipfsHash": ipfs_hash,
                "lastVerified": datetime.now(timezone.utc),
                "lastUpdated": datetime.now(timezone.utc),
                "criticalMetadata": critical_metadata,
                "nonCriticalMetadata": non_critical_metadata or {},
                "isCurrent": True,
                "isDeleted": False,
                "previousVersionId": str(latest_doc["_id"]),
                "documentHistory": [*latest_doc.get("documentHistory", []), str(latest_doc["_id"])]
            }
            
            # Insert the new version
            result = self.assets_collection.insert_one(new_doc)
            new_doc_id = str(result.inserted_id)
            
            # Record transaction
            self.record_transaction(
                asset_id,
                "VERSION_CREATE",
                wallet_address,
                metadata={
                    "versionNumber": new_version_number,
                    "previousVersionId": str(latest_doc["_id"])
                }
            )
            
            return new_doc_id
                
        except Exception as e:
            logger.error(f"Error creating new version: {str(e)}")
            raise

    def soft_delete(self, asset_id: str, deleted_by: str) -> bool:
        """Soft delete the current version of a document"""
        try:
            # Get current document first
            document = self.assets_collection.find_one({
                "assetId": asset_id,
                "isCurrent": True
            })
            
            if not document:
                return False
                
            # Update document
            update_result = self.assets_collection.update_one(
                {"_id": document["_id"]},
                {
                    "$set": {
                        "isDeleted": True,
                        "deletedAt": datetime.now(timezone.utc),
                        "deletedBy": deleted_by
                    }
                }
            )
            
            if update_result.modified_count > 0:
                # Record the transaction
                self.record_transaction(
                    asset_id,
                    "DELETE",
                    deleted_by,
                    metadata={
                        "originalOwner": document["walletAddress"],
                        "versionNumber": document["versionNumber"]
                    }
                )
                return True
                
            return False
            
        except Exception as e:
            logger.error(f"Error soft deleting document: {str(e)}")
            raise

    def record_transaction(self, asset_id: str, action: str, wallet_address: str, metadata: dict = None):
        """Record a transaction in the transaction history with optional metadata"""
        try:
            transaction = {
                "assetId": asset_id,  
                "action": action,
                "walletAddress": wallet_address,
                "timestamp": datetime.now(timezone.utc)
            }
            
            if metadata:
                transaction["metadata"] = metadata
                
            logger.info(f"Attempting to record transaction: {transaction}")
            
            result = self.transaction_collection.insert_one(transaction)
            
            logger.info(f"Transaction recorded successfully with id: {result.inserted_id}")
            
        except Exception as e:
            logger.error(f"Error recording transaction: {str(e)}")
            logger.exception("Full traceback:")

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
