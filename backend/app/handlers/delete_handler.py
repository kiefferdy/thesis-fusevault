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
                metadata = {
                    "reason": reason if reason else "User requested deletion",
                    "blockchain_tx_hash": blockchain_tx_hash
                }
                
                transaction_id = await self.transaction_service.record_transaction(
                    asset_id=asset_id,
                    action="DELETE",
                    wallet_address=wallet_address,
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
                metadata = {
                    "reason": reason if reason else "User requested deletion",
                    "blockchain_tx_hash": blockchain_tx_hash,
                    "owner_address": owner_address
                }
                
                transaction_id = await self.transaction_service.record_transaction(
                    asset_id=asset_id,
                    action="DELETE",
                    wallet_address=initiator_address,
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
