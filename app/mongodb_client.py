import os
from typing import Dict, Any, Optional, List
from datetime import datetime
import pymongo
from dotenv import load_dotenv

class MongoDBClient:
    _instance = None

    def __new__(cls):
        """
        Implement singleton pattern to ensure only one database connection exists.
        """
        if cls._instance is None:
            cls._instance = super(MongoDBClient, cls).__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        """
        Initialize MongoDB connection using environment variables.
        Only runs once due to singleton pattern.
        """
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
            self.client = pymongo.MongoClient(self.mongo_uri)
            
            # Test connection
            self.client.admin.command('ping')
            print("Successfully connected to MongoDB Atlas")
            
            # Initialize database and collections
            self.db = self.client.get_database("fusevault")
            self.domain_collection = self.db["domain"]
            
            # Create indexes
            self._create_indexes()
            
            self._initialized = True
            
        except Exception as e:
            raise ConnectionError(f"Failed to connect to MongoDB Atlas: {str(e)}")

    def _create_indexes(self) -> None:
        """
        Create necessary indexes for the collections.
        """
        try:
            # Create compound index for assetId and userWalletAddress
            self.domain_collection.create_index(
                [
                    ("assetId", pymongo.ASCENDING),
                    ("userWalletAddress", pymongo.ASCENDING)
                ],
                unique=True
            )

            # Create index for IPFS hash lookups
            self.domain_collection.create_index([("ipfsHash", pymongo.ASCENDING)])
            
            # Create index for smart contract transaction ID lookups
            self.domain_collection.create_index([("smartContractTxId", pymongo.ASCENDING)])
            
        except Exception as e:
            print(f"Warning: Failed to create indexes: {str(e)}")

    async def insert_document(self,
                            asset_id: str,
                            user_wallet_address: str,
                            smart_contract_tx_id: str,
                            ipfs_hash: str,
                            critical_metadata: Dict[str, Any],
                            non_critical_metadata: Optional[Dict[str, Any]] = None) -> str:
        """
        Insert a new document into MongoDB.
        
        Args:
            asset_id: Unique identifier for the asset
            user_wallet_address: User's Ethereum wallet address
            smart_contract_tx_id: Transaction hash from the smart contract
            ipfs_hash: CIDv1 hash of the data stored in IPFS
            critical_metadata: Dictionary containing critical metadata
            non_critical_metadata: Optional dictionary containing non-critical metadata
            
        Returns:
            str: ID of the inserted document
        """
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
            
            result = self.domain_collection.insert_one(document)
            return str(result.inserted_id)
            
        except pymongo.errors.DuplicateKeyError:
            raise ValueError(f"Document with asset ID {asset_id} already exists")
        except Exception as e:
            raise Exception(f"Error inserting document: {str(e)}")

    async def get_document_by_id(self, document_id: str) -> Dict[str, Any]:
        """
        Retrieve a document by its ID.
        
        Args:
            document_id: MongoDB document ID
            
        Returns:
            Dict containing the document data
        """
        try:
            document = await self.domain_collection.find_one({"_id": pymongo.ObjectId(document_id)})
            if not document:
                raise ValueError(f"Document with ID {document_id} not found")
            return document
        except Exception as e:
            raise Exception(f"Error retrieving document: {str(e)}")

    async def get_documents_by_wallet(self, wallet_address: str) -> List[Dict[str, Any]]:
        """
        Retrieve all documents associated with a wallet address.
        
        Args:
            wallet_address: User's Ethereum wallet address
            
        Returns:
            List of documents
        """
        try:
            cursor = self.domain_collection.find({
                "userWalletAddress": wallet_address,
                "isDeleted": False
            })
            return await cursor.to_list(length=None)
        except Exception as e:
            raise Exception(f"Error retrieving documents: {str(e)}")

    async def update_document(self,
                            document_id: str,
                            smart_contract_tx_id: str,
                            ipfs_hash: str,
                            critical_metadata: Dict[str, Any],
                            non_critical_metadata: Optional[Dict[str, Any]] = None) -> bool:
        """
        Update an existing document.
        
        Args:
            document_id: ID of the document to update
            smart_contract_tx_id: New transaction hash
            ipfs_hash: New IPFS hash
            critical_metadata: Updated critical metadata
            non_critical_metadata: Updated non-critical metadata
            
        Returns:
            bool: True if update was successful
        """
        try:
            current_doc = await self.get_document_by_id(document_id)
            
            # Add current version to history
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
                {"_id": pymongo.ObjectId(document_id)},
                {"$set": update_data}
            )
            
            return result.modified_count > 0
            
        except Exception as e:
            raise Exception(f"Error updating document: {str(e)}")

    async def verify_document(self, document_id: str) -> bool:
        """
        Update the lastVerified timestamp of a document.
        
        Args:
            document_id: ID of the document to verify
            
        Returns:
            bool: True if verification was successful
        """
        try:
            result = await self.domain_collection.update_one(
                {"_id": pymongo.ObjectId(document_id)},
                {"$set": {"lastVerified": datetime.utcnow()}}
            )
            return result.modified_count > 0
        except Exception as e:
            raise Exception(f"Error verifying document: {str(e)}")

    async def soft_delete(self, document_id: str) -> bool:
        """
        Mark a document as deleted (soft delete).
        
        Args:
            document_id: ID of the document to delete
            
        Returns:
            bool: True if deletion was successful
        """
        try:
            result = await self.domain_collection.update_one(
                {"_id": pymongo.ObjectId(document_id)},
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

    def close_connection(self):
        """
        Close the MongoDB connection.
        """
        if hasattr(self, 'client'):
            self.client.close()