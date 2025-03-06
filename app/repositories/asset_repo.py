from typing import Dict, Any, List, Optional
from datetime import datetime, timezone
from pymongo import DESCENDING
from bson import ObjectId
import logging

logger = logging.getLogger(__name__)

class AssetRepository:
    """
    Repository for asset operations in MongoDB.
    Handles document versioning, metadata management, and asset queries.
    """
    
    def __init__(self, db_client):
        """
        Initialize with MongoDB client.
        
        Args:
            db_client: The MongoDB client with initialized collections
        """
        self.assets_collection = db_client.assets_collection
        
    async def insert_asset(
        self, 
        asset_id: str, 
        wallet_address: str,
        smart_contract_tx_id: str, 
        ipfs_hash: str,
        critical_metadata: Dict[str, Any],
        non_critical_metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Insert a new asset document.
        
        Args:
            asset_id: Unique identifier for the asset
            wallet_address: Owner's wallet address
            smart_contract_tx_id: Transaction hash from blockchain
            ipfs_hash: CID from IPFS storage
            critical_metadata: Core metadata stored on blockchain
            non_critical_metadata: Additional metadata stored only in MongoDB
            
        Returns:
            String ID of the inserted document
        """
        try:
            document = {
                "assetId": asset_id,
                "versionNumber": 1,  # Initial version
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
            
            logger.info(f"Asset document inserted with ID: {doc_id}")
            return doc_id
            
        except Exception as e:
            logger.error(f"Error inserting asset: {str(e)}")
            raise
            
    async def find_asset(
        self, 
        asset_id: str, 
        version: Optional[int] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Find an asset by ID and optionally version.
        
        Args:
            asset_id: The asset ID to find
            version: Optional version number (default: current version)
            
        Returns:
            Asset document if found, None otherwise
        """
        try:
            # Set up the query
            query = {"assetId": asset_id, "isDeleted": False}
            
            if version:
                query["versionNumber"] = version
            else:
                query["isCurrent"] = True
                
            # Find the document
            asset = self.assets_collection.find_one(query)
            
            # Convert ObjectId to string if asset found
            if asset:
                asset["_id"] = str(asset["_id"])
                
            return asset
            
        except Exception as e:
            logger.error(f"Error finding asset: {str(e)}")
            raise
            
    async def find_assets_by_wallet(
        self, 
        wallet_address: str, 
        include_all_versions: bool = False
    ) -> List[Dict[str, Any]]:
        """
        Find assets by wallet address.
        
        Args:
            wallet_address: The wallet address to find assets for
            include_all_versions: Whether to include non-current versions
            
        Returns:
            List of asset documents
        """
        try:
            # Set up the query
            query = {"walletAddress": wallet_address, "isDeleted": False}
            
            if not include_all_versions:
                query["isCurrent"] = True
                
            # Find the documents
            cursor = self.assets_collection.find(query).sort("lastUpdated", DESCENDING)
            assets = list(cursor)
            
            # Convert ObjectId to string for each asset
            for asset in assets:
                asset["_id"] = str(asset["_id"])
                
            return assets
            
        except Exception as e:
            logger.error(f"Error finding assets by wallet: {str(e)}")
            raise
            
    async def create_new_version(
        self,
        asset_id: str,
        wallet_address: str,
        smart_contract_tx_id: str,
        ipfs_hash: str,
        critical_metadata: Dict[str, Any],
        non_critical_metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Create a new version of an existing asset.
        
        Args:
            asset_id: The asset ID to create a new version for
            wallet_address: Owner's wallet address
            smart_contract_tx_id: Transaction hash from blockchain
            ipfs_hash: CID from IPFS storage
            critical_metadata: Core metadata stored on blockchain
            non_critical_metadata: Additional metadata stored only in MongoDB
            
        Returns:
            String ID of the new version document
        """
        try:
            # Find the current version
            current_asset = self.assets_collection.find_one(
                {"assetId": asset_id, "isCurrent": True}
            )
            
            if not current_asset:
                raise ValueError(f"Asset not found: {asset_id}")
                
            # Get the current version number and increment
            new_version_number = current_asset.get("versionNumber", 1) + 1
            
            # Mark the current version as not current (FIRST, to avoid race conditions)
            self.assets_collection.update_one(
                {"_id": current_asset["_id"]},
                {"$set": {"isCurrent": False}}
            )
            
            # Create the new version document
            new_doc = {
                "assetId": asset_id,
                "versionNumber": new_version_number,
                "walletAddress": wallet_address,
                "smartContractTxId": smart_contract_tx_id,
                "ipfsHash": ipfs_hash,
                "lastVerified": datetime.now(timezone.utc),
                "lastUpdated": datetime.now(timezone.utc),
                "criticalMetadata": critical_metadata,
                "nonCriticalMetadata": non_critical_metadata or {},
                "isCurrent": True,
                "isDeleted": False,
                "previousVersionId": str(current_asset["_id"]),
                "documentHistory": [*current_asset.get("documentHistory", []), str(current_asset["_id"])]
            }
            
            # Insert the new version
            result = self.assets_collection.insert_one(new_doc)
            new_doc_id = str(result.inserted_id)
            
            logger.info(f"New version created for asset {asset_id}: {new_doc_id}")
            return new_doc_id
            
        except Exception as e:
            logger.error(f"Error creating new version: {str(e)}")
            raise
            
    async def update_non_critical_metadata(
        self, 
        asset_id: str, 
        metadata: Dict[str, Any]
    ) -> bool:
        """
        Update only non-critical metadata for an asset.
        
        Args:
            asset_id: The asset ID to update
            metadata: New non-critical metadata
            
        Returns:
            True if updated successfully, False otherwise
        """
        try:
            result = self.assets_collection.update_one(
                {"assetId": asset_id, "isCurrent": True},
                {"$set": {
                    "nonCriticalMetadata": metadata,
                    "lastUpdated": datetime.now(timezone.utc)
                }}
            )
            
            return result.modified_count > 0
            
        except Exception as e:
            logger.error(f"Error updating non-critical metadata: {str(e)}")
            raise
            
    async def soft_delete(self, asset_id: str, deleted_by: str) -> bool:
        """
        Soft delete an asset (mark as deleted).
        
        Args:
            asset_id: The asset ID to delete
            deleted_by: Wallet address that initiated the deletion
            
        Returns:
            True if deleted successfully, False otherwise
        """
        try:
            result = self.assets_collection.update_one(
                {"assetId": asset_id, "isCurrent": True},
                {"$set": {
                    "isDeleted": True,
                    "deletedBy": deleted_by,
                    "deletedAt": datetime.now(timezone.utc)
                }}
            )
            
            return result.modified_count > 0
            
        except Exception as e:
            logger.error(f"Error soft deleting asset: {str(e)}")
            raise
            
    async def get_version_history(self, asset_id: str) -> List[Dict[str, Any]]:
        """
        Get the version history for an asset.
        
        Args:
            asset_id: The asset ID to get history for
            
        Returns:
            List of asset versions ordered by version number
        """
        try:
            cursor = self.assets_collection.find(
                {"assetId": asset_id}
            ).sort("versionNumber", 1)
            
            versions = list(cursor)
            
            # Convert ObjectId to string for each version
            for version in versions:
                version["_id"] = str(version["_id"])
                
            return versions
            
        except Exception as e:
            logger.error(f"Error getting version history: {str(e)}")
            raise
