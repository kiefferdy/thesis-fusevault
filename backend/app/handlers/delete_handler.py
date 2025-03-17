from typing import List, Optional
import logging
from fastapi import HTTPException

from app.services.asset_service import AssetService
from app.services.transaction_service import TransactionService
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
        transaction_service: TransactionService = None
    ):
        """
        Initialize with required services.
        
        Args:
            asset_service: Service for asset operations
            transaction_service: Optional service for recording transactions
        """
        self.asset_service = asset_service
        self.transaction_service = transaction_service
        
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
                # For now, only allow the asset owner to delete their assets
                raise HTTPException(
                    status_code=403,
                    detail=f"Unauthorized: Only the asset owner can delete this asset"
                )
                
            # Soft delete the asset
            success = await self.asset_service.soft_delete(asset_id, wallet_address)
            
            if not success:
                raise HTTPException(
                    status_code=500,
                    detail=f"Failed to delete asset with ID {asset_id}"
                )
                
            # Record the transaction if transaction service is available
            transaction_id = None
            if self.transaction_service:
                metadata = {"reason": reason} if reason else {}
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
