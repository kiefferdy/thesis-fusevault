import os
import logging
from typing import Dict, Any, Optional, List
from datetime import datetime
from motor.motor_asyncio import AsyncIOMotorClient
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
            # Initialize MongoDB connection using motor
            self.client = AsyncIOMotorClient(self.mongo_uri)
            
            # Initialize database and collections
            self.db = self.client.get_database("fusevault")
            self.domain_collection = self.db["domain"]
            
            self._initialized = True
            
        except Exception as e:
            raise ConnectionError(f"Failed to connect to MongoDB Atlas: {str(e)}")

    async def insert_document(self, asset_id: str, user_wallet_address: str,
                            smart_contract_tx_id: str, ipfs_hash: str,
                            critical_metadata: Dict[str, Any],
                            non_critical_metadata: Optional[Dict[str, Any]] = None) -> str:
        """Insert a new document into MongoDB"""
        try:
            document = {
                "assetId": asset_id,
                "userWalletAddress": user_wallet_address,
                "smartContractTxId": smart_contract_tx_id,
                "ipfsHash": ipfs_hash,
                "lastVerified": datetime.utcnow(),
                "lastUpdated": datetime.utcnow(),
                "criticalMetadata": critical_metadata,
                "nonCriticalMetadata": non_critical_metadata or {},
                "isCurrent": True,
                "isDeleted": False,
                "documentHistory": [],
                "version": 1
            }
            
            result = await self.domain_collection.insert_one(document)
            return str(result.inserted_id)
            
        except Exception as e:
            logger.error(f"Error inserting document: {str(e)}")
            raise Exception(f"Error inserting document: {str(e)}")

    async def get_document_by_id(self, document_id: str) -> Dict[str, Any]:
        try:
            # Validate ObjectId format
            if not ObjectId.is_valid(document_id):
                raise ValueError(f"Invalid document ID format: {document_id}")
                
            # Convert string ID to ObjectId
            obj_id = ObjectId(document_id)
            
            # Find the document
            document = await self.domain_collection.find_one({"_id": obj_id})
            if not document:
                raise ValueError(f"Document with ID {document_id} not found")
                
            # Convert ObjectId to string for JSON serialization
            document['_id'] = str(document['_id'])
            return document
            
        except Exception as e:
            logger.error(f"Error retrieving document: {str(e)}")
            raise

    async def get_documents_by_wallet(self, wallet_address: str) -> List[Dict[str, Any]]:
        try:
            cursor = self.domain_collection.find({
                "userWalletAddress": wallet_address,
                "isDeleted": False
            })
            return await cursor.to_list(length=None)
        except Exception as e:
            logger.error(f"Error retrieving documents: {str(e)}")
            raise

    async def ensure_indexes(self) -> None:
        try:
            await self.domain_collection.create_index(
                [("assetId", 1), ("userWalletAddress", 1)],
                unique=True
            )
            await self.domain_collection.create_index([("ipfsHash", 1)])
            await self.domain_collection.create_index([("smartContractTxId", 1)])
        except Exception as e:
            logger.error(f"Failed to create indexes: {str(e)}")
            raise

    async def close_connection(self):
        if hasattr(self, 'client'):
            self.client.close()