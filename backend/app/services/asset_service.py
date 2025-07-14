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
        non_critical_metadata: Optional[Dict[str, Any]] = None,
        ipfs_version: Optional[int] = None
    ) -> str:
        """
        Create a new asset document in MongoDB.
        
        If an asset with the same ID exists but is marked as deleted, and the wallet address
        matches the original owner, this method will permanently delete all previous versions
        of the asset that are marked as deleted, and create a fresh version 1 document.
        
        Args:
            asset_id: Unique identifier for the asset
            wallet_address: Owner's wallet address
            smart_contract_tx_id: Transaction hash from blockchain
            ipfs_hash: CID from IPFS storage
            critical_metadata: Core metadata stored on blockchain
            non_critical_metadata: Additional metadata stored only in MongoDB
            ipfs_version: Optional specific blockchain IPFS version (defaults to 1 for new assets)
                
        Returns:
            String ID of the created document
                
        Raises:
            ValueError: If asset already exists and is not deleted, or if a deleted
                    asset exists but is owned by a different wallet address
        """
        try:
            # Check if asset already exists and is not deleted
            existing_asset = await self.asset_repository.find_asset({
                "assetId": asset_id,
                "isCurrent": True,
                "isDeleted": False
            })
            
            if existing_asset:
                raise ValueError(f"Asset with ID {asset_id} already exists")
            
            # Check if there's a deleted asset with this ID
            deleted_asset = await self.asset_repository.find_asset({
                "assetId": asset_id,
                "isDeleted": True
            })
            
            if deleted_asset:
                # If the owner is trying to recreate their own deleted asset
                if deleted_asset.get("walletAddress", "").lower() == wallet_address.lower():
                    # Delete all previous versions of this asset that are marked as deleted
                    deleted_count = await self.asset_repository.delete_assets({
                        "assetId": asset_id,
                        "isDeleted": True
                    })
                    
                    logger.info(f"Deleted {deleted_count} previous versions of asset {asset_id} before recreation")
                    
                    # Create a new document with version 1
                    document = {
                        "assetId": asset_id,
                        "versionNumber": 1,
                        "ipfsVersion": ipfs_version or 1,
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
                    
                    logger.info(f"Recreated asset with ID: {doc_id}, after deleting previous versions")
                    return doc_id
                else:
                    # Different owner can't reuse the ID
                    raise ValueError(f"Asset with ID {asset_id} exists but is owned by a different wallet")
            
            # Create document for MongoDB (normal flow for new assets)
            document = {
                "assetId": asset_id,
                "versionNumber": 1,
                "ipfsVersion": ipfs_version or 1,
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
            
    async def get_asset_with_deleted(
        self, 
        asset_id: str, 
        version: Optional[int] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Get an asset by ID and optionally version, including deleted assets.
        
        Args:
            asset_id: The asset ID to find
            version: Optional version number (default: current version)
            
        Returns:
            Asset document if found, None otherwise
        """
        try:
            # Build query
            query = {"assetId": asset_id}
            
            if version:
                query["versionNumber"] = version
            else:
                query["isCurrent"] = True
                
            # Find asset
            return await self.asset_repository.find_asset(query)
            
        except Exception as e:
            logger.error(f"Error getting asset with deleted: {str(e)}")
            raise
            
    async def get_documents_by_wallet(
        self, 
        wallet_address: str, 
        include_all_versions: bool = False,
        include_deleted: bool = False
    ) -> List[Dict[str, Any]]:
        """
        Get assets owned by a specific wallet address.
        
        Args:
            wallet_address: The wallet address to find assets for
            include_all_versions: Whether to include non-current versions
            include_deleted: Whether to include deleted assets
            
        Returns:
            List of asset documents
        """
        try:
            # Build query
            query = {"walletAddress": wallet_address}
            
            if not include_deleted:
                query["isDeleted"] = False
                
            if not include_all_versions:
                query["isCurrent"] = True
                
            # Find assets
            return await self.asset_repository.find_assets(query)
            
        except Exception as e:
            logger.error(f"Error getting documents by wallet: {str(e)}")
            raise
            
    async def get_user_assets(self, wallet_address: str) -> List[Dict[str, Any]]:
        """
        Get all assets owned by a specific wallet address.
        Only returns current versions that are not deleted.
        Formats the response to match frontend expectations.
        
        Args:
            wallet_address: The wallet address to get assets for
            
        Returns:
            List of assets owned by the wallet
        """
        try:
            logger.info(f"Getting assets for wallet: {wallet_address}")
            
            # Updated query to support case-insensitive address matching
            # Some wallet addresses might be stored with different capitalization
            normalized_address = wallet_address.lower()
            
            # Create a query that matches regardless of case
            # MongoDB regex with options 'i' for case-insensitive
            query = {
                "$or": [
                    {"walletAddress": normalized_address},
                    {"walletAddress": {"$regex": f"^{normalized_address}$", "$options": "i"}}
                ]
            }
            
            # Also ensure we're only getting current and non-deleted assets
            query["isCurrent"] = True
            query["isDeleted"] = False
            
            # Find assets directly with the query instead of using get_documents_by_wallet
            assets = await self.asset_repository.find_assets(query)

            # Log asset count for monitoring
            if len(assets) > 0:
                logger.debug(f"Found {len(assets)} assets from DB for wallet: {wallet_address}")
            
            # Format assets for frontend compatibility
            formatted_assets = []
            for asset in assets:
                # Get creation time from version 1 of this asset
                asset_id_val = asset.get("assetId")
                try:
                    first_version = await self.asset_repository.find_asset({
                        "assetId": asset_id_val,
                        "versionNumber": 1
                    })
                    
                    if first_version:
                        # Handle case where _id might be a string (convert to ObjectId)
                        version_id = first_version["_id"]
                        if isinstance(version_id, str):
                            try:
                                version_id = ObjectId(version_id)
                            except Exception:
                                version_id = None
                        
                        if version_id and hasattr(version_id, 'generation_time'):
                            created_at = version_id.generation_time.isoformat()
                        else:
                            created_at = asset.get("lastUpdated", "")
                    else:
                        created_at = asset.get("lastUpdated", "")
                except Exception as e:
                    logger.warning(f"Could not find version 1 for asset {asset_id_val}: {e}")
                    # Fallback to current document's ObjectId or lastUpdated
                    if hasattr(asset["_id"], 'generation_time'):
                        created_at = asset["_id"].generation_time.isoformat()
                    else:
                        created_at = asset.get("lastUpdated", "")
                
                # Convert datetime objects to ISO strings if needed
                if hasattr(created_at, 'isoformat'):
                    created_at = created_at.isoformat()
                
                # Handle updated_at conversion
                updated_at = asset.get("lastUpdated", "")
                if hasattr(updated_at, 'isoformat'):
                    updated_at = updated_at.isoformat()
                
                # Format the asset data to match frontend expectations
                formatted_asset = {
                    "_id": asset["_id"],
                    "assetId": asset.get("assetId", ""),
                    "walletAddress": asset.get("walletAddress", ""),
                    "criticalMetadata": asset.get("criticalMetadata", {}),
                    "nonCriticalMetadata": asset.get("nonCriticalMetadata", {}),
                    "ipfsCid": asset.get("ipfsHash", ""),
                    "versionNumber": asset.get("versionNumber", 1),
                    "createdAt": created_at,
                    "updatedAt": updated_at
                }
                formatted_assets.append(formatted_asset)
            
            return formatted_assets
            
        except Exception as e:
            logger.error(f"Error getting user assets: {str(e)}")
            # Return empty list on error to prevent frontend crashes
            return []
            
    async def create_new_version(
        self,
        asset_id: str,
        wallet_address: str,
        smart_contract_tx_id: str,
        ipfs_hash: str,
        critical_metadata: Dict[str, Any],
        non_critical_metadata: Optional[Dict[str, Any]] = None,
        ipfs_version: Optional[int] = None,
        performed_by: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Create a new version of an existing asset in MongoDB.
        
        Args:
            asset_id: The asset ID to create new version for
            wallet_address: Owner's wallet address (preserved across versions)
            smart_contract_tx_id: Transaction hash from blockchain
            ipfs_hash: CID from IPFS storage
            critical_metadata: Core metadata stored on blockchain
            non_critical_metadata: Additional metadata stored only in MongoDB
            ipfs_version: Optional specific blockchain IPFS version (if None, will be set to versionNumber)
            performed_by: Optional wallet address of who performed this action (for delegation tracking)
            
        Returns:
            Dict containing new document ID and version number
            
        Raises:
            ValueError: If asset not found
        """
        try:
            # Find current version, including deleted ones
            current_asset = await self.asset_repository.find_asset(
                {"assetId": asset_id, "isCurrent": True}
            )
            
            if not current_asset:
                raise ValueError(f"Asset not found: {asset_id}")
                
            # Get current version number and increment
            new_version_number = current_asset.get("versionNumber", 1) + 1
            
            # Check if the asset is currently deleted
            was_deleted = current_asset.get("isDeleted", False)
            
            # Determine the ipfsVersion to use
            if ipfs_version is None:
                current_ipfs_version = current_asset.get("ipfsVersion", current_asset.get("versionNumber", 1))
                ipfs_version = new_version_number
                
                # If blockchain_tx_id is the same, this is likely just a non-critical update
                if smart_contract_tx_id == current_asset.get("smartContractTxId"):
                    ipfs_version = current_ipfs_version
            
            # Mark current version as not current first
            await self.asset_repository.update_asset(
                {"_id": ObjectId(current_asset["_id"])},
                {"$set": {"isCurrent": False}}
            )
            
            # Create new version document
            new_doc = {
                "assetId": asset_id,
                "versionNumber": new_version_number,
                "ipfsVersion": ipfs_version,
                "walletAddress": wallet_address,  # This preserves the original owner
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
            
            # Add delegation audit trail if action was performed by someone else
            if performed_by and performed_by.lower() != wallet_address.lower():
                new_doc["performedBy"] = performed_by
                new_doc["isDelegatedAction"] = True
            else:
                new_doc["isDelegatedAction"] = False
            
            # Insert new version
            new_doc_id = await self.asset_repository.insert_asset(new_doc)
            
            logger.info(f"New version created for asset {asset_id}: {new_doc_id}")
            return {
                "document_id": new_doc_id,
                "version_number": new_version_number,
                "ipfs_version": ipfs_version,
                "was_deleted": was_deleted
            }
            
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
        This marks ALL versions of the asset as deleted, not just the current version.
        
        Args:
            asset_id: The asset ID to delete
            deleted_by: Wallet address that initiated the deletion
            
        Returns:
            True if deleted successfully, False otherwise
        """
        try:
            # Get the deletion timestamp - use the same timestamp for all versions
            deletion_time = datetime.now(timezone.utc)
            
            # Mark all versions of this asset as deleted
            result = await self.asset_repository.update_assets(
                {"assetId": asset_id},
                {"$set": {
                    "isDeleted": True,
                    "deletedBy": deleted_by,
                    "deletedAt": deletion_time
                }}
            )
            
            logger.info(f"Soft delete for asset {asset_id}: modified {result} documents")
            return result > 0
            
        except Exception as e:
            logger.error(f"Error soft deleting asset: {str(e)}")
            raise
            
    async def get_version_history(self, asset_id: str, include_deleted: bool = False) -> List[Dict[str, Any]]:
        """
        Get the version history for an asset.
        
        Args:
            asset_id: The asset ID to get history for
            include_deleted: Whether to include deleted versions (default: False)
            
        Returns:
            List of asset versions ordered by version number
        """
        try:
            # Build query based on deletion status
            query = {"assetId": asset_id}
            
            if not include_deleted:
                query["isDeleted"] = False
                
            return await self.asset_repository.find_assets(
                query,
                sort_field="versionNumber",
                sort_direction=1  # Ascending order
            )
            
        except Exception as e:
            logger.error(f"Error getting version history: {str(e)}")
            raise
