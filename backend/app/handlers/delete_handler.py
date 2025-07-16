from typing import List, Optional, Dict, Any
import logging
from fastapi import HTTPException

from app.services.asset_service import AssetService
from app.services.blockchain_service import BlockchainService
from app.services.transaction_service import TransactionService
from app.services.transaction_state_service import TransactionStateService
from app.schemas.delete_schema import DeleteResponse, BatchDeleteResponse

logger = logging.getLogger(__name__)

class DeleteHandler:
    """
    Handler for asset deletion operations.
    Acts as a bridge between API routes and the service layer.
    """
    
    def __init__(
        self, 
        asset_service: AssetService,
        blockchain_service: BlockchainService = None,
        transaction_service: TransactionService = None,
        transaction_state_service: TransactionStateService = None,
        auth_context: Optional[Dict[str, Any]] = None
    ):
        """
        Initialize with required services.
        
        Args:
            asset_service: Service for asset operations
            blockchain_service: Service for blockchain operations
            transaction_service: Optional service for recording transactions
            transaction_state_service: Service for managing pending transactions
            auth_context: Authentication context for the current request
        """
        self.asset_service = asset_service
        self.blockchain_service = blockchain_service
        self.transaction_service = transaction_service
        self.transaction_state_service = transaction_state_service or TransactionStateService()
        self.auth_context = auth_context
        
    async def delete_asset(
        self,
        asset_id: str,
        wallet_address: str,
        reason: Optional[str] = None
    ) -> DeleteResponse:
        """
        Soft delete an asset.
        
        Args:
            asset_id: The asset ID to delete
            wallet_address: The wallet address performing the deletion
            reason: Optional reason for deletion
            
        Returns:
            DeleteResponse containing deletion result
            
        Raises:
            HTTPException: If asset not found or deletion fails
        """
        try:
            # Check if the asset exists
            asset = await self.asset_service.get_asset(asset_id)
            
            if not asset:
                raise HTTPException(
                    status_code=404,
                    detail=f"Asset with ID {asset_id} not found"
                )
                
            # Check if the asset is already deleted
            if asset.get("isDeleted", False):
                return DeleteResponse(
                    asset_id=asset_id,
                    status="warning",
                    message="Asset is already deleted",
                    document_id=asset["_id"]
                )
                
            # Check if the user has permission to delete
            # Only asset owner or an admin can delete an asset
            asset_owner = asset.get("walletAddress", "").lower()
            requester = wallet_address.lower()
            
            if asset_owner != requester:
                # In a real application, you would check if the requester has admin privileges
                # or delegate permissions with the new contract
                if self.blockchain_service:
                    try:
                        # Check if the asset exists on the blockchain and get ownership
                        asset_exists = await self.blockchain_service.check_asset_exists(
                            asset_id=asset_id,
                            owner_address=asset_owner
                        )
                        
                        if not asset_exists["exists"] or asset_exists["is_deleted"]:
                            raise HTTPException(
                                status_code=404,
                                detail=f"Asset with ID {asset_id} not found on blockchain or already deleted"
                            )
                            
                        # Call the blockchain operation to delete the asset on behalf of the owner
                        # This will fail if the caller doesn't have admin/delegate permission
                        blockchain_result = await self.blockchain_service.delete_asset_for(
                            asset_id=asset_id,
                            owner_address=asset_owner
                        )
                        
                        # If we get here, it means the requester has permission on the blockchain
                        logger.info(f"Blockchain deletion successful for asset {asset_id} on behalf of {asset_owner}. TX: {blockchain_result['tx_hash']}")
                        
                    except Exception as blockchain_error:
                        logger.error(f"Error validating permissions on blockchain: {str(blockchain_error)}")
                        # If blockchain check fails, fall back to standard check
                        raise HTTPException(
                            status_code=403,
                            detail=f"Unauthorized: Only the asset owner can delete this asset"
                        )
                else:
                    # No blockchain service available, use standard check
                    raise HTTPException(
                        status_code=403,
                        detail=f"Unauthorized: Only the asset owner can delete this asset"
                    )
                
            # Handle blockchain deletion based on authentication method
            blockchain_tx_hash = None
            if self.blockchain_service:
                try:
                    # Check if this is a wallet user (needs to sign transaction)
                    if self.auth_context and self.auth_context.get("auth_method") == "wallet":
                        # For wallet users, prepare unsigned transaction and return for signing
                        if asset_owner == requester:
                            # Regular deletion (owner deleting their own asset)
                            blockchain_result = await self.blockchain_service.delete_asset(asset_id, self.auth_context)
                        else:
                            # Delegate deleting on behalf of owner
                            blockchain_result = await self.blockchain_service.delete_asset_for(
                                asset_id=asset_id,
                                owner_address=asset_owner,
                                auth_context=self.auth_context
                            )
                        
                        if not blockchain_result.get("success"):
                            raise Exception(f"Failed to prepare transaction: {blockchain_result.get('error')}")
                        
                        # Store pending transaction state
                        pending_data = {
                            "asset_id": asset_id,
                            "owner_address": asset_owner,
                            "initiator_address": wallet_address,
                            "action": "deleteAsset" if asset_owner == requester else "deleteAssetFor",
                            "reason": reason,
                            "transaction": blockchain_result["transaction"],
                            "asset_document_id": asset["_id"]
                        }
                        
                        pending_tx_id = await self.transaction_state_service.store_pending_transaction(
                            user_address=wallet_address,
                            transaction_data=pending_data
                        )
                        
                        # Return transaction for frontend to sign
                        return DeleteResponse(
                            asset_id=asset_id,
                            status="pending_signature",
                            message="Deletion transaction prepared for signing",
                            pending_tx_id=pending_tx_id,
                            transaction=blockchain_result["transaction"],
                            estimated_gas=blockchain_result.get("estimated_gas"),
                            gas_price=blockchain_result.get("gas_price"),
                            function_name=blockchain_result.get("function_name"),
                            next_step="sign_and_broadcast"
                        )
                    
                    else:
                        # For API key users, use existing server-signed logic
                        if asset_owner == requester:
                            # Regular deletion (owner deleting their own asset)
                            blockchain_result = await self.blockchain_service.delete_asset(asset_id)
                        else:
                            # We already verified permissions above, this is a delegate/admin deleting on behalf of owner
                            blockchain_result = await self.blockchain_service.delete_asset_for(
                                asset_id=asset_id,
                                owner_address=asset_owner
                            )
                        
                        blockchain_tx_hash = blockchain_result.get("tx_hash")
                        logger.info(f"Asset {asset_id} deleted on blockchain. TX: {blockchain_tx_hash}")
                    
                except Exception as e:
                    logger.error(f"Blockchain deletion failed for asset {asset_id}: {str(e)}")
                    # Continue with database deletion even if blockchain deletion fails
                    # The reconciliation process can handle this later
            
            # Soft delete the asset in the database
            success = await self.asset_service.soft_delete(asset_id, wallet_address)
            
            if not success:
                raise HTTPException(
                    status_code=500,
                    detail=f"Failed to delete asset with ID {asset_id}"
                )
                
            # Record the transaction if transaction service is available
            transaction_id = None
            if self.transaction_service:
                performed_by = wallet_address if wallet_address.lower() != asset_owner.lower() else asset_owner
                
                metadata = {
                    "reason": reason if reason else "User requested deletion",
                    "smartContractTxId": blockchain_tx_hash,
                    "ownerAddress": asset_owner
                }
                
                transaction_id = await self.transaction_service.record_transaction(
                    asset_id=asset_id,
                    action="DELETE",
                    wallet_address=asset_owner,
                    performed_by=performed_by,
                    metadata=metadata
                )
                
            return DeleteResponse(
                asset_id=asset_id,
                status="success",
                message="Asset deleted successfully",
                document_id=asset["_id"],
                transaction_id=transaction_id
            )
            
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error deleting asset: {str(e)}")
            raise HTTPException(status_code=500, detail=f"Error deleting asset: {str(e)}")
    
    async def complete_blockchain_deletion(
        self,
        pending_tx_id: str,
        blockchain_tx_hash: str,
        initiator_address: str
    ) -> DeleteResponse:
        """
        Complete the deletion process after blockchain transaction is confirmed.
        
        Args:
            pending_tx_id: ID of the pending transaction
            blockchain_tx_hash: Hash of the confirmed blockchain transaction
            initiator_address: Address of the user who initiated the transaction
            
        Returns:
            DeleteResponse with completion results
        """
        try:
            # Get pending transaction data
            pending_data = await self.transaction_state_service.get_pending_transaction(pending_tx_id)
            
            if not pending_data:
                raise Exception(f"Pending transaction {pending_tx_id} not found or expired")
            
            # Verify the initiator
            if pending_data.get("initiator_address", "").lower() != initiator_address.lower():
                raise Exception("Unauthorized: initiator address mismatch")
            
            # Extract data from pending transaction
            asset_id = pending_data["asset_id"]
            owner_address = pending_data["owner_address"]
            reason = pending_data.get("reason")
            asset_document_id = pending_data.get("asset_document_id")
            
            # Verify transaction was successful
            if self.blockchain_service:
                tx_verification = await self.blockchain_service.verify_transaction_success(blockchain_tx_hash)
                if not tx_verification.get("success"):
                    raise Exception(f"Blockchain transaction failed or not found: {blockchain_tx_hash}")
            
            # Soft delete the asset in the database
            success = await self.asset_service.soft_delete(asset_id, initiator_address)
            
            if not success:
                raise Exception(f"Failed to delete asset with ID {asset_id} in database")
            
            # Record the transaction if transaction service is available
            transaction_id = None
            if self.transaction_service:
                performed_by = initiator_address if initiator_address.lower() != owner_address.lower() else owner_address
                
                metadata = {
                    "reason": reason if reason else "User requested deletion",
                    "smartContractTxId": blockchain_tx_hash,
                    "owner_address": owner_address
                }
                
                transaction_id = await self.transaction_service.record_transaction(
                    asset_id=asset_id,
                    action="DELETE",
                    wallet_address=owner_address,
                    performed_by=performed_by,
                    metadata=metadata
                )
            
            # Clean up pending transaction
            await self.transaction_state_service.remove_pending_transaction(pending_tx_id)
            
            logger.info(f"Successfully completed blockchain deletion for asset {asset_id}")
            
            return DeleteResponse(
                asset_id=asset_id,
                status="success",
                message="Asset deleted successfully",
                document_id=asset_document_id,
                transaction_id=transaction_id,
                blockchain_tx_hash=blockchain_tx_hash
            )
            
        except Exception as e:
            logger.error(f"Error completing blockchain deletion: {str(e)}")
            raise HTTPException(status_code=500, detail=f"Error completing deletion: {str(e)}")
    
    async def batch_delete_assets(
        self,
        asset_ids: List[str],
        wallet_address: str,
        reason: Optional[str] = None
    ) -> BatchDeleteResponse:
        """
        Batch delete multiple assets.
        
        Args:
            asset_ids: List of asset IDs to delete
            wallet_address: The wallet address performing the deletion
            reason: Optional reason for deletion
            
        Returns:
            BatchDeleteResponse containing batch deletion results
            
        Raises:
            HTTPException: If batch deletion fails
        """
        try:
            results = {}
            success_count = 0
            failure_count = 0
            
            for asset_id in asset_ids:
                try:
                    delete_result = await self.delete_asset(
                        asset_id=asset_id,
                        wallet_address=wallet_address,
                        reason=reason
                    )
                    results[asset_id] = {
                        "status": delete_result.status,
                        "message": delete_result.message,
                        "document_id": delete_result.document_id,
                        "transaction_id": delete_result.transaction_id
                    }
                    if delete_result.status in ["success", "warning"]:
                        success_count += 1
                    else:
                        failure_count += 1
                except HTTPException as http_e:
                    results[asset_id] = {
                        "status": "error",
                        "message": http_e.detail
                    }
                    failure_count += 1
                except Exception as e:
                    results[asset_id] = {
                        "status": "error",
                        "message": str(e)
                    }
                    failure_count += 1
                    
            # Determine overall status
            overall_status = "success" if failure_count == 0 else "partial" if success_count > 0 else "error"
            
            # Craft overall message
            if overall_status == "success":
                message = f"All {success_count} assets deleted successfully"
            elif overall_status == "partial":
                message = f"{success_count} assets deleted successfully, {failure_count} failed"
            else:
                message = f"Failed to delete any of the {failure_count} assets"
                
            return BatchDeleteResponse(
                status=overall_status,
                message=message,
                results=results,
                success_count=success_count,
                failure_count=failure_count
            )
            
        except Exception as e:
            logger.error(f"Error batch deleting assets: {str(e)}")
            raise HTTPException(status_code=500, detail=f"Error batch deleting assets: {str(e)}")
    
    async def prepare_batch_deletion(
        self,
        asset_ids: List[str], 
        initiator_address: str,
        reason: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Prepare batch deletion with MetaMask signing support and API key delegation validation.
        
        Args:
            asset_ids: List of asset IDs to delete
            initiator_address: The wallet address of the user initiating the batch deletion
            reason: Optional reason for deletion
            
        Returns:
            Dict with batch preparation results
        """
        try:
            # Validate batch size
            if len(asset_ids) > 50:  # Match smart contract limit
                return {
                    "status": "error",
                    "message": "Batch size exceeds maximum of 50 assets",
                    "asset_count": len(asset_ids)
                }
            
            if len(asset_ids) == 0:
                return {
                    "status": "error", 
                    "message": "Must provide at least one asset ID",
                    "asset_count": 0
                }
            
            # Step 1: Validate all assets and check ownership/permissions
            validated_assets = []  # Assets that need blockchain deletion
            already_deleted_assets = []  # Assets already deleted on blockchain (need DB sync)
            owner_address_to_assets = {}  # Group assets by owner for efficient blockchain operations
            
            for idx, asset_id in enumerate(asset_ids):
                try:
                    # Get asset from database
                    asset = await self.asset_service.get_asset(asset_id)
                    
                    if not asset:
                        raise ValueError(f"Asset {asset_id} not found")
                    
                    # Check if already deleted
                    if asset.get("isDeleted", False):
                        raise ValueError(f"Asset {asset_id} is already deleted")
                    
                    owner_address = asset.get("walletAddress", "").lower()
                    
                    if not owner_address:
                        raise ValueError(f"Asset {asset_id} has no owner address")
                    
                    # SECURITY: For API key auth, validate delegation permissions
                    if self.auth_context and self.auth_context.get("auth_method") == "api_key":
                        if owner_address != initiator_address.lower():
                            # User is trying to delete assets for a different wallet
                            # Validate delegation permissions
                            server_wallet = self.blockchain_service.get_server_wallet_address()
                            
                            try:
                                # Check if target wallet delegated the API key user
                                is_user_delegated = await self.blockchain_service.check_delegation(
                                    owner_address=owner_address,
                                    delegate_address=initiator_address
                                )
                                
                                # Check if target wallet delegated the server wallet  
                                is_server_delegated = await self.blockchain_service.check_delegation(
                                    owner_address=owner_address,
                                    delegate_address=server_wallet
                                )
                                
                                # Both delegations are required for API key operations
                                if not is_user_delegated and not is_server_delegated:
                                    raise ValueError(
                                        f"Wallet {owner_address} has not delegated either you ({initiator_address}) "
                                        f"or the server wallet ({server_wallet}). "
                                        f"For API key access, both delegations are required. "
                                        f"Ask {owner_address} to call: "
                                        f"setDelegate('{initiator_address}', true) AND "
                                        f"setDelegate('{server_wallet}', true)"
                                    )
                                elif not is_user_delegated:
                                    raise ValueError(
                                        f"Wallet {owner_address} has not delegated you ({initiator_address}). "
                                        f"Cannot delete assets for this wallet via API key. "
                                        f"Ask {owner_address} to call setDelegate('{initiator_address}', true)"
                                    )
                                elif not is_server_delegated:
                                    raise ValueError(
                                        f"Wallet {owner_address} has not delegated the server wallet ({server_wallet}). "
                                        f"Cannot delete assets for this wallet via API key. "
                                        f"Ask {owner_address} to call setDelegate('{server_wallet}', true)"
                                    )
                                    
                            except Exception as e:
                                if "has not delegated" in str(e):
                                    raise e  # Re-raise our clear error message
                                else:
                                    raise ValueError(f"Unable to verify delegation for {owner_address}: {str(e)}")
                    
                    # Verify asset exists on blockchain and check if already deleted
                    blockchain_already_deleted = False
                    if self.blockchain_service:
                        try:
                            asset_exists = await self.blockchain_service.check_asset_exists(
                                asset_id=asset_id,
                                owner_address=owner_address
                            )
                            
                            if not asset_exists["exists"] or asset_exists["is_deleted"]:
                                # Asset is already deleted on blockchain - sync database state
                                blockchain_already_deleted = True
                                logger.info(f"Asset {asset_id} already deleted on blockchain, syncing database state")
                                
                        except Exception as e:
                            logger.warning(f"Could not verify asset {asset_id} on blockchain: {str(e)}")
                            # Continue with deletion attempt - blockchain verification is not critical
                    
                    # Handle assets based on blockchain status
                    if blockchain_already_deleted:
                        # Asset already deleted on blockchain - add to sync list
                        already_deleted_assets.append({
                            "asset_id": asset_id,
                            "owner_address": owner_address,
                            "document_id": asset.get("_id"),
                            "index": idx
                        })
                    else:
                        # Asset needs blockchain deletion - group by owner for efficient batch operations
                        if owner_address not in owner_address_to_assets:
                            owner_address_to_assets[owner_address] = []
                        
                        owner_address_to_assets[owner_address].append({
                            "asset_id": asset_id,
                            "owner_address": owner_address,
                            "document_id": asset.get("_id"),
                            "index": idx
                        })
                        
                        validated_assets.append({
                            "asset_id": asset_id,
                            "owner_address": owner_address,
                            "document_id": asset.get("_id"),
                            "index": idx
                        })
                    
                except Exception as e:
                    logger.error(f"Validation error for asset {asset_id}: {str(e)}")
                    return {
                        "status": "error",
                        "message": f"Validation failed for asset {asset_id}: {str(e)}",
                        "asset_count": len(asset_ids)
                    }
            
            # Handle assets that are already deleted on blockchain (sync database)
            synced_results = {}
            if already_deleted_assets:
                logger.info(f"Syncing database state for {len(already_deleted_assets)} assets already deleted on blockchain")
                
                for asset_data in already_deleted_assets:
                    try:
                        asset_id = asset_data["asset_id"]
                        
                        # Sync database state - mark as deleted
                        success = await self.asset_service.soft_delete(
                            asset_id=asset_id,
                            deleted_by=initiator_address
                        )
                        
                        if success:
                            # Record transaction for the sync operation
                            if self.transaction_service:
                                owner_address = asset_data["owner_address"]
                                performed_by = initiator_address if initiator_address.lower() != owner_address.lower() else owner_address
                                
                                await self.transaction_service.record_transaction(
                                    asset_id=asset_id,
                                    action="DELETE",
                                    wallet_address=owner_address,
                                    performed_by=performed_by,
                                    metadata={
                                        "reason": reason or "Database sync - asset already deleted on blockchain",
                                        "sync_operation": True,
                                        "owner_address": owner_address
                                    }
                                )
                            
                            synced_results[asset_id] = {
                                "status": "synced",
                                "message": "Database synced - asset was already deleted on blockchain",
                                "document_id": asset_data.get("document_id")
                            }
                        else:
                            synced_results[asset_id] = {
                                "status": "error",
                                "message": "Failed to sync database state"
                            }
                            
                    except Exception as e:
                        logger.error(f"Error syncing asset {asset_data.get('asset_id', 'unknown')}: {str(e)}")
                        synced_results[asset_data.get("asset_id", "unknown")] = {
                            "status": "error",
                            "message": f"Database sync failed: {str(e)}"
                        }
            
            # Check if we have any assets that need blockchain transactions
            if not validated_assets:
                # All assets were already deleted on blockchain - return sync results
                sync_success_count = sum(1 for result in synced_results.values() if result["status"] == "synced")
                sync_failure_count = len(synced_results) - sync_success_count
                
                if sync_success_count > 0:
                    message = f"Database synced: {sync_success_count} assets were already deleted on blockchain"
                    if sync_failure_count > 0:
                        message += f" ({sync_failure_count} sync failures)"
                else:
                    message = f"All {len(already_deleted_assets)} assets were already deleted on blockchain, but database sync failed"
                    
                return {
                    "status": "success" if sync_failure_count == 0 else "partial",
                    "message": message,
                    "asset_count": len(asset_ids),
                    "results": synced_results,
                    "success_count": sync_success_count,
                    "failure_count": sync_failure_count
                }
            
            # Step 2: Prepare blockchain transaction(s)
            if self.blockchain_service:
                # Check authentication method to determine transaction signing approach
                if self.auth_context and self.auth_context.get("auth_method") == "wallet":
                    # For wallet users, prepare unsigned transaction for MetaMask signing
                    try:
                        # Determine if we need single or multiple blockchain transactions
                        if len(owner_address_to_assets) == 1:
                            # Single owner - use batch delete function
                            owner_address = list(owner_address_to_assets.keys())[0]
                            asset_ids_for_owner = [asset["asset_id"] for asset in owner_address_to_assets[owner_address]]
                            
                            if owner_address == initiator_address.lower():
                                # User deleting their own assets
                                blockchain_result = await self.blockchain_service.batch_delete_assets(
                                    asset_ids=asset_ids_for_owner,
                                    auth_context=self.auth_context
                                )
                            else:
                                # Delegate deleting on behalf of owner
                                blockchain_result = await self.blockchain_service.batch_delete_assets_for(
                                    owner_address=owner_address,
                                    asset_ids=asset_ids_for_owner,
                                    auth_context=self.auth_context
                                )
                        else:
                            # Multiple owners - would need multiple transactions (not supported yet)
                            return {
                                "status": "error",
                                "message": "Batch deletion across multiple asset owners is not supported yet",
                                "asset_count": len(asset_ids)
                            }
                        
                        if not blockchain_result.get("success"):
                            raise Exception(f"Failed to prepare transaction: {blockchain_result.get('error')}")
                        
                        # Store pending transaction state
                        pending_data = {
                            "asset_ids": asset_ids,
                            "validated_assets": validated_assets,
                            "synced_results": synced_results,  # Include synced assets results
                            "initiator_address": initiator_address,
                            "reason": reason,
                            "transaction": blockchain_result["transaction"],
                            "owner_addresses": list(owner_address_to_assets.keys())
                        }
                        
                        pending_tx_id = await self.transaction_state_service.store_pending_transaction(
                            user_address=initiator_address,
                            transaction_data=pending_data
                        )
                        
                        # Calculate synced assets for user feedback
                        synced_count = len(already_deleted_assets)
                        if synced_count > 0:
                            message = f"Sign transaction to delete {len(validated_assets)} assets in batch ({synced_count} assets already deleted on blockchain, database synced)"
                        else:
                            message = f"Sign transaction to delete {len(validated_assets)} assets in batch"
                        
                        # Return transaction for frontend to sign
                        return {
                            "status": "pending_signature",
                            "message": message,
                            "asset_count": len(asset_ids),
                            "validated_count": len(validated_assets),
                            "synced_count": synced_count,
                            "pending_tx_id": pending_tx_id,
                            "transaction": blockchain_result["transaction"],
                            "estimated_gas": blockchain_result.get("estimated_gas"),
                            "gas_price": blockchain_result.get("gas_price"),
                            "function_name": blockchain_result.get("function_name"),
                        }
                    
                    except Exception as e:
                        logger.error(f"Error preparing blockchain transaction: {str(e)}")
                        return {
                            "status": "error",
                            "message": f"Failed to prepare blockchain transaction: {str(e)}",
                            "asset_count": len(asset_ids)
                        }
                
                else:
                    # For API key users, execute deletion directly with server wallet
                    try:
                        deleted_assets = []
                        failed_assets = []
                        
                        # Process each owner group separately
                        for owner_address, assets_for_owner in owner_address_to_assets.items():
                            asset_ids_for_owner = [asset["asset_id"] for asset in assets_for_owner]
                            
                            try:
                                if owner_address == initiator_address.lower():
                                    # User deleting their own assets  
                                    blockchain_result = await self.blockchain_service.batch_delete_assets(
                                        asset_ids=asset_ids_for_owner
                                    )
                                else:
                                    # API key user deleting on behalf of delegated owner
                                    blockchain_result = await self.blockchain_service.batch_delete_assets_for(
                                        owner_address=owner_address,
                                        asset_ids=asset_ids_for_owner
                                    )
                                
                                # Mark assets as deleted in database
                                for asset in assets_for_owner:
                                    success = await self.asset_service.soft_delete(
                                        asset_id=asset["asset_id"], 
                                        deleted_by=initiator_address
                                    )
                                    
                                    if success:
                                        deleted_assets.append({
                                            "asset_id": asset["asset_id"],
                                            "status": "success",
                                            "message": "Asset deleted successfully",
                                            "document_id": asset["document_id"]
                                        })
                                        
                                        # Record transaction
                                        if self.transaction_service:
                                            performed_by = initiator_address if initiator_address.lower() != owner_address.lower() else owner_address
                                            
                                            await self.transaction_service.record_transaction(
                                                asset_id=asset["asset_id"],
                                                action="DELETE",
                                                wallet_address=owner_address,
                                                performed_by=performed_by,
                                                metadata={
                                                    "reason": reason or "Batch deletion via API key",
                                                    "smartContractTxId": blockchain_result.get("tx_hash"),
                                                    "owner_address": owner_address
                                                }
                                            )
                                    else:
                                        failed_assets.append({
                                            "asset_id": asset["asset_id"],
                                            "status": "error", 
                                            "message": "Failed to delete asset in database"
                                        })
                                        
                            except Exception as e:
                                logger.error(f"Error deleting assets for owner {owner_address}: {str(e)}")
                                for asset in assets_for_owner:
                                    failed_assets.append({
                                        "asset_id": asset["asset_id"],
                                        "status": "error",
                                        "message": f"Deletion failed: {str(e)}"
                                    })
                        
                        # Prepare results
                        all_results = {}
                        for result in deleted_assets + failed_assets:
                            all_results[result["asset_id"]] = result
                        
                        success_count = len(deleted_assets)
                        failure_count = len(failed_assets)
                        
                        overall_status = "success" if failure_count == 0 else "partial" if success_count > 0 else "error"
                        
                        if overall_status == "success":
                            message = f"All {success_count} assets deleted successfully"
                        elif overall_status == "partial":
                            message = f"{success_count} assets deleted successfully, {failure_count} failed"
                        else:
                            message = f"Failed to delete any of the {failure_count} assets"
                        
                        return {
                            "status": overall_status,
                            "message": message,
                            "asset_count": len(asset_ids),
                            "results": all_results,
                            "success_count": success_count,
                            "failure_count": failure_count
                        }
                        
                    except Exception as e:
                        logger.error(f"Error in API key batch deletion: {str(e)}")
                        return {
                            "status": "error",
                            "message": f"Batch deletion failed: {str(e)}",
                            "asset_count": len(asset_ids)
                        }
            
            else:
                # No blockchain service - just delete from database
                logger.warning("No blockchain service available, performing database-only deletion")
                
                results = {}
                success_count = 0
                failure_count = 0
                
                for asset in validated_assets:
                    try:
                        success = await self.asset_service.soft_delete(
                            asset_id=asset["asset_id"],
                            deleted_by=initiator_address
                        )
                        
                        if success:
                            results[asset["asset_id"]] = {
                                "status": "success", 
                                "message": "Asset deleted successfully (database only)",
                                "document_id": asset["document_id"]
                            }
                            success_count += 1
                        else:
                            results[asset["asset_id"]] = {
                                "status": "error",
                                "message": "Failed to delete asset in database"
                            }
                            failure_count += 1
                            
                    except Exception as e:
                        results[asset["asset_id"]] = {
                            "status": "error",
                            "message": f"Deletion failed: {str(e)}"
                        }
                        failure_count += 1
                
                overall_status = "success" if failure_count == 0 else "partial" if success_count > 0 else "error"
                
                return {
                    "status": overall_status,
                    "message": f"{success_count} assets deleted, {failure_count} failed (database only)",
                    "asset_count": len(asset_ids),
                    "results": results,
                    "success_count": success_count,
                    "failure_count": failure_count
                }
                
        except Exception as e:
            logger.error(f"Error preparing batch deletion: {str(e)}")
            return {
                "status": "error",
                "message": f"Batch deletion preparation failed: {str(e)}",
                "asset_count": len(asset_ids) if asset_ids else 0
            }
    
    async def complete_batch_blockchain_deletion(
        self,
        pending_tx_id: str,
        blockchain_tx_hash: str,
        initiator_address: str
    ) -> Dict[str, Any]:
        """
        Complete batch deletion after blockchain transaction is confirmed.
        
        Args:
            pending_tx_id: ID of the pending transaction
            blockchain_tx_hash: Hash of the confirmed blockchain transaction
            initiator_address: Address of the user who initiated the transaction
            
        Returns:
            Dict with completion results
        """
        try:
            # Get pending transaction data
            pending_data = await self.transaction_state_service.get_pending_transaction(pending_tx_id)
            
            if not pending_data:
                raise Exception(f"Pending transaction {pending_tx_id} not found or expired")
            
            # Verify the initiator
            if pending_data.get("initiator_address", "").lower() != initiator_address.lower():
                raise Exception("Unauthorized: initiator address mismatch")
            
            # Extract data from pending transaction
            asset_ids = pending_data.get("asset_ids", [])
            validated_assets = pending_data.get("validated_assets", [])
            synced_results = pending_data.get("synced_results", {})  # Results from database sync
            reason = pending_data.get("reason")
            
            if not asset_ids or not validated_assets:
                raise Exception("Invalid pending transaction data: missing asset information")
            
            # Verify transaction was successful
            if self.blockchain_service:
                tx_verification = await self.blockchain_service.verify_transaction_success(blockchain_tx_hash)
                if not tx_verification.get("success"):
                    revert_reason = tx_verification.get("revert_reason", "Unknown reason")
                    raise Exception(f"Blockchain transaction failed: {revert_reason} (TX: {blockchain_tx_hash})")
            
            # Delete all assets in database
            results = []
            success_count = 0
            failure_count = 0
            
            for asset_data in validated_assets:
                try:
                    asset_id = asset_data["asset_id"]
                    owner_address = asset_data["owner_address"]
                    document_id = asset_data.get("document_id")
                    
                    # Soft delete the asset in the database
                    success = await self.asset_service.soft_delete(
                        asset_id=asset_id,
                        deleted_by=initiator_address
                    )
                    
                    if success:
                        # Record transaction
                        transaction_id = None
                        if self.transaction_service:
                            performed_by = initiator_address if initiator_address.lower() != owner_address.lower() else owner_address
                            
                            transaction_id = await self.transaction_service.record_transaction(
                                asset_id=asset_id,
                                action="DELETE",
                                wallet_address=owner_address,
                                performed_by=performed_by,
                                metadata={
                                    "reason": reason or "Batch deletion via MetaMask",
                                    "smartContractTxId": blockchain_tx_hash,
                                    "batch_deletion": True,
                                    "batch_id": pending_tx_id,
                                    "owner_address": owner_address
                                }
                            )
                        
                        results.append({
                            "asset_id": asset_id,
                            "status": "success",
                            "message": "Asset deleted successfully",
                            "document_id": document_id,
                            "transaction_id": transaction_id
                        })
                        success_count += 1
                        
                    else:
                        results.append({
                            "asset_id": asset_id,
                            "status": "error",
                            "message": "Failed to delete asset in database",
                            "document_id": document_id
                        })
                        failure_count += 1
                    
                except Exception as e:
                    logger.error(f"Error deleting asset {asset_data.get('asset_id', 'unknown')}: {str(e)}")
                    results.append({
                        "asset_id": asset_data.get("asset_id", "unknown"),
                        "status": "error",
                        "message": f"Deletion failed: {str(e)}",
                        "document_id": asset_data.get("document_id")
                    })
                    failure_count += 1
            
            # Clean up pending transaction
            await self.transaction_state_service.remove_pending_transaction(pending_tx_id)
            
            # Prepare results dictionary - combine blockchain deletion and sync results
            results_dict = {}
            
            # Add blockchain deletion results
            for result in results:
                results_dict[result["asset_id"]] = {
                    "status": result["status"],
                    "message": result["message"],
                    "document_id": result.get("document_id"),
                    "transaction_id": result.get("transaction_id")
                }
            
            # Add synced results (assets already deleted on blockchain)
            for asset_id, sync_result in synced_results.items():
                results_dict[asset_id] = sync_result
                if sync_result["status"] == "synced":
                    success_count += 1
                else:
                    failure_count += 1
            
            # Determine overall status
            total_processed = len(results_dict)
            blockchain_deleted = len(results)
            synced_count = len(synced_results)
            overall_status = "success" if failure_count == 0 else "partial" if success_count > 0 else "error"
            
            # Craft overall message
            if overall_status == "success":
                if synced_count > 0 and blockchain_deleted > 0:
                    message = f"Batch operation completed: {blockchain_deleted} assets deleted on blockchain, {synced_count} database records synced"
                elif synced_count > 0:
                    message = f"Database sync completed: {synced_count} assets were already deleted on blockchain"
                else:
                    message = f"Batch deletion completed: all {success_count} assets deleted successfully"
            elif overall_status == "partial":
                message = f"Batch operation completed: {success_count}/{total_processed} successful, {failure_count} failed"
            else:
                message = f"Batch operation failed: could not process any of the {failure_count} assets"
            
            logger.info(f"Batch deletion completed: {success_count} successes, {failure_count} failures")
            
            return {
                "status": overall_status,
                "message": message,
                "asset_count": total_processed,
                "results": results_dict,
                "blockchain_tx_hash": blockchain_tx_hash,
                "success_count": success_count,
                "failure_count": failure_count
            }
            
        except Exception as e:
            logger.error(f"Error completing batch deletion: {str(e)}")
            return {
                "status": "error",
                "message": f"Batch deletion completion failed: {str(e)}",
                "asset_count": 0
            }
