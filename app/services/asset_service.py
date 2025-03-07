from typing import Optional, Dict, Any, List
from datetime import datetime, timezone
import logging
from bson import ObjectId
from app.repositories.asset_repo import AssetRepository

logger = logging.getLogger(__name__)

class AssetService:
    """
    Service for asset-related operations.
    Handles asset creation, retrieval, updates, and versioning in MongoDB.
    """
    
    def __init__(self, asset_repository: AssetRepository):
        """
        Initialize with repository.
        
        Args:
            asset_repository: Repository for asset data access
        """
        self.asset_repository = asset_repository
        
    async def create_asset(
        self, 
        asset_id: str, 
        wallet_address: str,
        smart_contract_tx_id: str,
        ipfs_hash: str,
        critical_metadata: Dict[str, Any],
        non_critical_metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Create a new asset document in MongoDB.
        
        Args:
            asset_id: Unique identifier for the asset
            wallet_address: Owner's wallet address
            smart_contract_tx_id: Transaction hash from blockchain
            ipfs_hash: CID from IPFS storage
            critical_metadata: Core metadata stored on blockchain
            non_critical_metadata: Additional metadata stored only in MongoDB
            
        Returns:
            String ID of the created document
            
        Raises:
            ValueError: If asset already exists
        """
        try:
            # Check if asset already exists
            existing_asset = await self.asset_repository.find_asset({"assetId": asset_id, "isCurrent": True})
            
            if existing_asset:
                raise ValueError(f"Asset with ID {asset_id} already exists")
                
            # Create document for MongoDB
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
            
            # Insert into MongoDB
            doc_id = await self.asset_repository.insert_asset(document)
            
            logger.info(f"Asset created with ID: {doc_id}")
            return doc_id
            
        except Exception as e:
            logger.error(f"Error creating asset: {str(e)}")
            raise
            
    async def get_asset(
        self, 
        asset_id: str, 
        version: Optional[int] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Get an asset by ID and optionally version.
        
        Args:
            asset_id: The asset ID to find
            version: Optional version number (default: current version)
            
        Returns:
            Asset document if found, None otherwise
        """
        try:
            # Build query
            query = {"assetId": asset_id, "isDeleted": False}
            
            if version:
                query["versionNumber"] = version
            else:
                query["isCurrent"] = True
                
            # Find asset
            return await self.asset_repository.find_asset(query)
            
        except Exception as e:
            logger.error(f"Error getting asset: {str(e)}")
            raise
            
    async def get_documents_by_wallet(
        self, 
        wallet_address: str, 
        include_all_versions: bool = False
    ) -> List[Dict[str, Any]]:
        """
        Get assets owned by a specific wallet address.
        
        Args:
            wallet_address: The wallet address to find assets for
            include_all_versions: Whether to include non-current versions
            
        Returns:
            List of asset documents
        """
        try:
            # Build query
            query = {"walletAddress": wallet_address, "isDeleted": False}
            
            if not include_all_versions:
                query["isCurrent"] = True
                
            # Find assets
            return await self.asset_repository.find_assets(query)
            
        except Exception as e:
            logger.error(f"Error getting documents by wallet: {str(e)}")
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
        Create a new version of an existing asset in MongoDB.
        
        Args:
            asset_id: The asset ID to create new version for
            wallet_address: Owner's wallet address
            smart_contract_tx_id: Transaction hash from blockchain
            ipfs_hash: CID from IPFS storage
            critical_metadata: Core metadata stored on blockchain
            non_critical_metadata: Additional metadata stored only in MongoDB
            
        Returns:
            String ID of the new version document
            
        Raises:
            ValueError: If asset not found
        """
        try:
            # Find current version
            current_asset = await self.asset_repository.find_asset(
                {"assetId": asset_id, "isCurrent": True}
            )
            
            if not current_asset:
                raise ValueError(f"Asset not found: {asset_id}")
                
            # Get current version number and increment
            new_version_number = current_asset.get("versionNumber", 1) + 1
            
            # Mark current version as not current first
            await self.asset_repository.update_asset(
                {"_id": ObjectId(current_asset["_id"])},
                {"$set": {"isCurrent": False}}
            )
            
            # Create new version document
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
                "previousVersionId": current_asset["_id"],
                "documentHistory": [*current_asset.get("documentHistory", []), current_asset["_id"]]
            }
            
            # Insert new version
            new_doc_id = await self.asset_repository.insert_asset(new_doc)
            
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
            return await self.asset_repository.update_asset(
                {"assetId": asset_id, "isCurrent": True},
                {"$set": {
                    "nonCriticalMetadata": metadata,
                    "lastUpdated": datetime.now(timezone.utc)
                }}
            )
            
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
            return await self.asset_repository.update_asset(
                {"assetId": asset_id, "isCurrent": True},
                {"$set": {
                    "isDeleted": True,
                    "deletedBy": deleted_by,
                    "deletedAt": datetime.now(timezone.utc)
                }}
            )
            
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
            return await self.asset_repository.find_assets(
                {"assetId": asset_id},
                sort_field="versionNumber",
                sort_direction=1  # Ascending order
            )
            
        except Exception as e:
            logger.error(f"Error getting version history: {str(e)}")
            raise
