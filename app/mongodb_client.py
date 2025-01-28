import os
import asyncio
from typing import Dict, Any, Optional, List
from datetime import datetime
from motor.motor_asyncio import AsyncIOMotorClient
from bson import ObjectId
from dotenv import load_dotenv

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
            
            # We'll create indexes when needed rather than at initialization
            self._initialized = True
            
        except Exception as e:
            raise ConnectionError(f"Failed to connect to MongoDB Atlas: {str(e)}")

    async def ensure_indexes(self) -> None:
        """Create necessary indexes for the collections if they don't exist."""
        try:
            # Create compound index for assetId and userWalletAddress
            await self.domain_collection.create_index(
                [
                    ("assetId", 1),
                    ("userWalletAddress", 1)
                ],
                unique=True
            )

            # Create index for IPFS hash lookups
            await self.domain_collection.create_index([("ipfsHash", 1)])
            
            # Create index for smart contract transaction ID lookups
            await self.domain_collection.create_index([("smartContractTxId", 1)])
            
        except Exception as e:
            print(f"Warning: Failed to create indexes: {str(e)}")

    async def insert_document(self, asset_id: str, user_wallet_address: str,
                            smart_contract_tx_id: str, ipfs_hash: str,
                            critical_metadata: Dict[str, Any],
                            non_critical_metadata: Optional[Dict[str, Any]] = None) -> str:
        try:
            # Ensure indexes exist before insertion
            await self.ensure_indexes()
            
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
            raise Exception(f"Error inserting document: {str(e)}")

    async def get_document_by_id(self, document_id: str) -> Dict[str, Any]:
        try:
            document = await self.domain_collection.find_one({"_id": ObjectId(document_id)})
            if not document:
                raise ValueError(f"Document with ID {document_id} not found")
            return document
        except Exception as e:
            raise Exception(f"Error retrieving document: {str(e)}")

    async def get_documents_by_wallet(self, wallet_address: str) -> List[Dict[str, Any]]:
        try:
            cursor = self.domain_collection.find({
                "userWalletAddress": wallet_address,
                "isDeleted": False
            })
            return await cursor.to_list(length=None)
        except Exception as e:
            raise Exception(f"Error retrieving documents: {str(e)}")

    async def update_document(self, document_id: str, smart_contract_tx_id: str,
                            ipfs_hash: str, critical_metadata: Dict[str, Any],
                            non_critical_metadata: Optional[Dict[str, Any]] = None) -> bool:
        try:
            current_doc = await self.get_document_by_id(document_id)
            
            history = current_doc.get('documentHistory', [])
            history.append(str(current_doc['_id']))
            
            update_data = {
                "smartContractTxId": smart_contract_tx_id,
                "ipfsHash": ipfs_hash,
                "lastUpdated": datetime.utcnow(),
                "criticalMetadata": critical_metadata,
                "nonCriticalMetadata": non_critical_metadata or {},
                "documentHistory": history,
                "version": current_doc['version'] + 1
            }
            
            result = await self.domain_collection.update_one(
                {"_id": ObjectId(document_id)},
                {"$set": update_data}
            )
            
            return result.modified_count > 0
            
        except Exception as e:
            raise Exception(f"Error updating document: {str(e)}")

    async def verify_document(self, document_id: str) -> bool:
        try:
            result = await self.domain_collection.update_one(
                {"_id": ObjectId(document_id)},
                {"$set": {"lastVerified": datetime.utcnow()}}
            )
            return result.modified_count > 0
        except Exception as e:
            raise Exception(f"Error verifying document: {str(e)}")

    async def soft_delete(self, document_id: str) -> bool:
        try:
            result = await self.domain_collection.update_one(
                {"_id": ObjectId(document_id)},
                {
                    "$set": {
                        "isDeleted": True,
                        "lastUpdated": datetime.utcnow(),
                        "isCurrent": False
                    }
                }
            )
            return result.modified_count > 0
        except Exception as e:
            raise Exception(f"Error deleting document: {str(e)}")

    async def close_connection(self):
        """Close the MongoDB connection."""
        if hasattr(self, 'client'):
            self.client.close()