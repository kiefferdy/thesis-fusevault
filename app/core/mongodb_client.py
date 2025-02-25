import os
import logging
from typing import Dict, Any, Optional, List
from datetime import datetime, timezone
from uuid import uuid4
from pymongo import MongoClient
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
            self.domain_collection = self.db["domain"]
            self.auth_collection = self.db["auth"]
            self.transaction_collection = self.db["transaction_history"]
            self.sessions_collection = self.db["sessions"]
            
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
            
            # Verify transaction collection exists
            if "transaction_history" not in collections:
                logger.warning("Transaction collection not found, creating it...")
                self.db.create_collection("transaction_history")
                
            # Log collection info
            logger.info(f"Transaction collection info: {self.transaction_collection.find_one()}")
        
        except Exception as e:
            logger.error(f"Error verifying collections: {str(e)}")

    def _create_indexes(self):
        """Create necessary indexes for collections"""
        try:
            # Domain collection indexes
            self.domain_collection.create_index([("assetId", 1), ("userWalletAddress", 1)])
            self.domain_collection.create_index([("ipfsHash", 1)])
            self.domain_collection.create_index([("smartContractTxId", 1)])
            
            # Auth collection indexes
            self.auth_collection.create_index([("walletAddress", 1)], unique=True)
            self.auth_collection.create_index([("email", 1)], unique=True)
            
            # Transaction history indexes
            self.transaction_collection.create_index([("documentId", 1)])
            self.transaction_collection.create_index([("timestamp", -1)])

            # Session collection indexes
            self.sessions_collection.create_index([("created_at", -1)], expireAfterSeconds=60)
            
            logger.info("Successfully created indexes")
        except Exception as e:
            logger.error(f"Failed to create indexes: {str(e)}")
            raise

    # Auth Methods
    def create_user(self, wallet_address: str, email: str, role: str = "user") -> str:
        """Create a new user"""
        try:
            user = {
                "walletAddress": wallet_address,
                "email": email,
                "role": role,
                "createdAt": datetime.now(timezone.utc),
                "lastLogin": None,
                "isActive": True
            }
            result = self.auth_collection.insert_one(user)
            return str(result.inserted_id)
        except Exception as e:
            logger.error(f"Error creating user: {str(e)}")
            raise

    def get_user_by_wallet(self, wallet_address: str) -> Optional[Dict]:
        """Retrieve user by wallet address"""
        try:
            user = self.auth_collection.find_one({"walletAddress": wallet_address})
            if user:
                user['_id'] = str(user['_id'])
            return user
        except Exception as e:
            logger.error(f"Error retrieving user: {str(e)}")
            raise

    # Session Management Methods
    def create_session(self, walletAddress: str) -> str:
        """Create a new session"""
        try:
            session_id = str(uuid4())
            session_data = {
                "_id": session_id,
                "walletAddress": walletAddress,
                "created_at": datetime.now(timezone.utc)
            }
            self.sessions_collection.delete_one({"walletAddress": walletAddress})
            result = self.sessions_collection.insert_one(session_data)
            return str(result.inserted_id)
        except Exception as e:
            logger.error(f"Error creating session: {str(e)}")
            raise
    
    def get_session(self, session_id: str):
        """Retrieve session id"""
        return self.sessions_collection.find_one({"_id": session_id})
    
    def delete_session(self, session_id: str):
        """Delete an existing session"""
        self.sessions_collection.delete_one({"_id": session_id})
         

    # Document Methods
    def insert_document(self, asset_id: str, user_wallet_address: str,
                       smart_contract_tx_id: str, ipfs_hash: str,
                       critical_metadata: Dict[str, Any],
                       non_critical_metadata: Optional[Dict[str, Any]] = None) -> str:
        """Insert a new document into MongoDB"""
        try:
            # First verify user exists
            user = self.get_user_by_wallet(user_wallet_address)
            if not user:
                raise ValueError("User not found")

            document = {
                "assetId": asset_id,
                "userWalletAddress": user_wallet_address,
                "smartContractTxId": smart_contract_tx_id,
                "ipfsHash": ipfs_hash,
                "lastVerified": datetime.now(timezone.utc),
                "lastUpdated": datetime.now(timezone.utc),
                "criticalMetadata": critical_metadata,
                "nonCriticalMetadata": non_critical_metadata or {},
                "isCurrent": True,
                "isDeleted": False,
                "documentHistory": [],
                "version": 1
            }
            
            result = self.domain_collection.insert_one(document)
            doc_id = str(result.inserted_id)
            
            # Record transaction
            self._record_transaction(doc_id, "CREATE", user_wallet_address)
            
            return doc_id
            
        except Exception as e:
            logger.error(f"Error inserting document: {str(e)}")
            raise

    def get_document_by_id(self, document_id: str) -> Dict[str, Any]:
        """Retrieve a document by its ID"""
        try:
            if not ObjectId.is_valid(document_id):
                raise ValueError(f"Invalid document ID format: {document_id}")
                
            obj_id = ObjectId(document_id)
            document = self.domain_collection.find_one({"_id": obj_id})
            
            if not document:
                raise ValueError(f"Document with ID {document_id} not found")
                
            document['_id'] = str(document['_id'])
            return document
            
        except Exception as e:
            logger.error(f"Error retrieving document: {str(e)}")
            raise

    def get_documents_by_wallet(self, wallet_address: str) -> List[Dict[str, Any]]:
        """Retrieve all documents for a wallet address"""
        try:
            cursor = self.domain_collection.find({
                "userWalletAddress": wallet_address,
                "isDeleted": False
            })
            documents = list(cursor)
            
            # Convert ObjectId to string for each document
            for doc in documents:
                doc['_id'] = str(doc['_id'])
                
            return documents
        except Exception as e:
            logger.error(f"Error retrieving documents: {str(e)}")
            raise

    def update_document(self, document_id: str, smart_contract_tx_id: str,
                       ipfs_hash: str, critical_metadata: Dict[str, Any],
                       non_critical_metadata: Optional[Dict[str, Any]] = None) -> bool:
        """Update an existing document"""
        try:
            obj_id = ObjectId(document_id)
            
            # Get the current document
            current_doc = self.domain_collection.find_one({"_id": obj_id})
            if not current_doc:
                return False

            # Update the document
            update_result = self.domain_collection.update_one(
                {"_id": obj_id},
                {
                    "$set": {
                        "smartContractTxId": smart_contract_tx_id,
                        "ipfsHash": ipfs_hash,
                        "criticalMetadata": critical_metadata,
                        "nonCriticalMetadata": non_critical_metadata or {},
                        "lastUpdated": datetime.now(timezone.utc),
                        "version": current_doc.get("version", 1) + 1
                    }
                }
            )
            
            if update_result.modified_count > 0:
                # Record transaction
                self._record_transaction(document_id, "UPDATE", current_doc["userWalletAddress"])
                return True
                
            return False
            
        except Exception as e:
            logger.error(f"Error updating document: {str(e)}")
            raise

    def verify_document(self, document_id: str) -> bool:
        """Verify a document's integrity"""
        try:
            obj_id = ObjectId(document_id)
            update_result = self.domain_collection.update_one(
                {"_id": obj_id},
                {"$set": {"lastVerified": datetime.now(timezone.utc)}}
            )
            return update_result.modified_count > 0
        except Exception as e:
            logger.error(f"Error verifying document: {str(e)}")
            raise

    def soft_delete(self, document_id: str, deleted_by: str) -> bool:
        """Soft delete with transaction recording"""
        try:
            obj_id = ObjectId(document_id)
            
            # Get current document first
            document = self.domain_collection.find_one({"_id": obj_id})
            if not document:
                return False
                
            # Update document
            update_result = self.domain_collection.update_one(
                {"_id": obj_id},
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
                self._record_transaction(
                    str(document["_id"]),  # Convert ObjectId to string
                    "DELETE",
                    deleted_by,
                    metadata={"originalOwner": document["userWalletAddress"]}
                )
                return True
                
            return False
            
        except Exception as e:
            logger.error(f"Error soft deleting document: {str(e)}")
            raise

    def _record_transaction(self, document_id: str, action: str, wallet_address: str, metadata: dict = None):
        """Record a transaction in the transaction history with optional metadata"""
        try:
            transaction = {
                "documentId": document_id,
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

    def close_connection(self):
        """Close the MongoDB connection"""
        if hasattr(self, 'client'):
            self.client.close()
            logger.info("MongoDB connection closed")