from typing import Optional, Dict, Any, List
import logging
from datetime import datetime, timezone
from pymongo import ASCENDING, DESCENDING, IndexModel
from pymongo.errors import DuplicateKeyError

logger = logging.getLogger(__name__)

class DelegationRepository:
    """
    Repository for delegation operations in MongoDB.
    Handles CRUD operations for the delegations collection.
    """
    
    def __init__(self, db_client):
        """
        Initialize with MongoDB client.
        
        Args:
            db_client: The MongoDB client with initialized collections
        """
        self.delegations_collection = db_client.delegations_collection
        
    async def create_indexes(self):
        """Create required indexes for the delegations collection"""
        indexes = [
            # Composite unique index for owner-delegate pair
            IndexModel([("ownerAddress", ASCENDING), ("delegateAddress", ASCENDING)], unique=True),
            # Index for querying delegations by owner
            IndexModel([("ownerAddress", ASCENDING), ("isActive", ASCENDING)]),
            # Index for querying delegations by delegate
            IndexModel([("delegateAddress", ASCENDING), ("isActive", ASCENDING)]),
            # Index for blockchain data
            IndexModel([("transactionHash", ASCENDING)], sparse=True),
            IndexModel([("blockNumber", ASCENDING)], sparse=True),
            # Index for time-based queries
            IndexModel([("createdAt", DESCENDING)]),
            IndexModel([("updatedAt", DESCENDING)])
        ]
        await self.delegations_collection.create_indexes(indexes)
        
    async def upsert_delegation(self, delegation_data: Dict[str, Any]) -> str:
        """
        Insert or update a delegation relationship.
        
        Args:
            delegation_data: Delegation data to upsert
            
        Returns:
            String ID of the upserted delegation
        """
        try:
            now = datetime.now(timezone.utc)
            
            # Prepare the update document
            update_doc = {
                "$set": {
                    "isActive": delegation_data.get("isActive", True),
                    "updatedAt": now
                },
                "$setOnInsert": {
                    "ownerAddress": delegation_data["ownerAddress"],
                    "delegateAddress": delegation_data["delegateAddress"],
                    "createdAt": now
                }
            }
            
            # Add optional fields if provided
            if "transactionHash" in delegation_data:
                update_doc["$set"]["transactionHash"] = delegation_data["transactionHash"]
            if "blockNumber" in delegation_data:
                update_doc["$set"]["blockNumber"] = delegation_data["blockNumber"]
            
            result = await self.delegations_collection.update_one(
                {
                    "ownerAddress": delegation_data["ownerAddress"],
                    "delegateAddress": delegation_data["delegateAddress"]
                },
                update_doc,
                upsert=True
            )
            
            # Get the document ID
            if result.upserted_id:
                delegation_id = str(result.upserted_id)
                logger.info(f"Delegation created with ID: {delegation_id}")
            else:
                # Find the updated document
                delegation = await self.delegations_collection.find_one({
                    "ownerAddress": delegation_data["ownerAddress"],
                    "delegateAddress": delegation_data["delegateAddress"]
                })
                delegation_id = str(delegation["_id"]) if delegation else None
                logger.info(f"Delegation updated with ID: {delegation_id}")
            
            return delegation_id
            
        except Exception as e:
            logger.error(f"Error upserting delegation: {str(e)}")
            raise
    
    async def get_delegations_by_owner(self, owner_address: str, active_only: bool = True) -> List[Dict[str, Any]]:
        """
        Get all delegations granted by a specific owner.
        
        Args:
            owner_address: The wallet address of the owner
            active_only: Whether to only return active delegations
            
        Returns:
            List of delegation documents
        """
        try:
            query = {"ownerAddress": owner_address.lower()}
            if active_only:
                query["isActive"] = True
                
            cursor = self.delegations_collection.find(query).sort("createdAt", DESCENDING)
            delegations = await cursor.to_list(length=None)
            
            # Convert ObjectId to string
            for delegation in delegations:
                delegation["id"] = str(delegation["_id"])
                del delegation["_id"]
                
            logger.info(f"Found {len(delegations)} delegations for owner {owner_address}")
            return delegations
            
        except Exception as e:
            logger.error(f"Error getting delegations by owner: {str(e)}")
            raise
    
    async def get_delegations_by_delegate(self, delegate_address: str, active_only: bool = True) -> List[Dict[str, Any]]:
        """
        Get all delegations received by a specific delegate.
        
        Args:
            delegate_address: The wallet address of the delegate
            active_only: Whether to only return active delegations
            
        Returns:
            List of delegation documents
        """
        try:
            query = {"delegateAddress": delegate_address.lower()}
            if active_only:
                query["isActive"] = True
                
            cursor = self.delegations_collection.find(query).sort("createdAt", DESCENDING)
            delegations = await cursor.to_list(length=None)
            
            # Convert ObjectId to string
            for delegation in delegations:
                delegation["id"] = str(delegation["_id"])
                del delegation["_id"]
                
            logger.info(f"Found {len(delegations)} delegations for delegate {delegate_address}")
            return delegations
            
        except Exception as e:
            logger.error(f"Error getting delegations by delegate: {str(e)}")
            raise
    
    async def get_delegation(self, owner_address: str, delegate_address: str) -> Optional[Dict[str, Any]]:
        """
        Get a specific delegation relationship.
        
        Args:
            owner_address: The wallet address of the owner
            delegate_address: The wallet address of the delegate
            
        Returns:
            Delegation document or None if not found
        """
        try:
            delegation = await self.delegations_collection.find_one({
                "ownerAddress": owner_address.lower(),
                "delegateAddress": delegate_address.lower()
            })
            
            if delegation:
                delegation["id"] = str(delegation["_id"])
                del delegation["_id"]
                
            return delegation
            
        except Exception as e:
            logger.error(f"Error getting delegation: {str(e)}")
            raise
    
    async def update_delegation_status(self, owner_address: str, delegate_address: str, 
                                     is_active: bool, transaction_hash: Optional[str] = None,
                                     block_number: Optional[int] = None) -> bool:
        """
        Update the active status of a delegation.
        
        Args:
            owner_address: The wallet address of the owner
            delegate_address: The wallet address of the delegate
            is_active: Whether the delegation should be active
            transaction_hash: Optional blockchain transaction hash
            block_number: Optional block number
            
        Returns:
            True if delegation was updated, False if not found
        """
        try:
            update_doc = {
                "isActive": is_active,
                "updatedAt": datetime.now(timezone.utc)
            }
            
            if transaction_hash:
                update_doc["transactionHash"] = transaction_hash
            if block_number:
                update_doc["blockNumber"] = block_number
                
            result = await self.delegations_collection.update_one(
                {
                    "ownerAddress": owner_address.lower(),
                    "delegateAddress": delegate_address.lower()
                },
                {"$set": update_doc}
            )
            
            success = result.modified_count > 0
            if success:
                logger.info(f"Updated delegation status: {owner_address} -> {delegate_address} = {is_active}")
            else:
                logger.warning(f"No delegation found to update: {owner_address} -> {delegate_address}")
                
            return success
            
        except Exception as e:
            logger.error(f"Error updating delegation status: {str(e)}")
            raise
    
    async def delete_delegation(self, owner_address: str, delegate_address: str) -> bool:
        """
        Delete a delegation relationship (rarely used - prefer updating status).
        
        Args:
            owner_address: The wallet address of the owner
            delegate_address: The wallet address of the delegate
            
        Returns:
            True if delegation was deleted, False if not found
        """
        try:
            result = await self.delegations_collection.delete_one({
                "ownerAddress": owner_address.lower(),
                "delegateAddress": delegate_address.lower()
            })
            
            success = result.deleted_count > 0
            if success:
                logger.info(f"Deleted delegation: {owner_address} -> {delegate_address}")
            else:
                logger.warning(f"No delegation found to delete: {owner_address} -> {delegate_address}")
                
            return success
            
        except Exception as e:
            logger.error(f"Error deleting delegation: {str(e)}")
            raise
    
    async def get_delegation_stats(self, wallet_address: str) -> Dict[str, int]:
        """
        Get delegation statistics for a wallet address.
        
        Args:
            wallet_address: The wallet address to get stats for
            
        Returns:
            Dictionary with delegation statistics
        """
        try:
            granted_count = await self.delegations_collection.count_documents({
                "ownerAddress": wallet_address.lower(),
                "isActive": True
            })
            
            received_count = await self.delegations_collection.count_documents({
                "delegateAddress": wallet_address.lower(),
                "isActive": True
            })
            
            total_count = granted_count + received_count
            
            return {
                "total_delegations": total_count,
                "delegations_granted": granted_count,
                "delegations_received": received_count
            }
            
        except Exception as e:
            logger.error(f"Error getting delegation stats: {str(e)}")
            raise
    
    async def sync_from_blockchain_event(self, event_data: Dict[str, Any]) -> str:
        """
        Sync delegation state from a blockchain event.
        
        Args:
            event_data: Event data from blockchain containing owner, delegate, status, etc.
            
        Returns:
            String ID of the synced delegation
        """
        try:
            delegation_data = {
                "ownerAddress": event_data["owner_address"].lower(),
                "delegateAddress": event_data["delegate_address"].lower(),
                "isActive": event_data["status"],
                "transactionHash": event_data["transaction_hash"],
                "blockNumber": event_data["block_number"]
            }
            
            return await self.upsert_delegation(delegation_data)
            
        except Exception as e:
            logger.error(f"Error syncing delegation from blockchain event: {str(e)}")
            raise