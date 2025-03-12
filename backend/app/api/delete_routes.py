from fastapi import APIRouter, Depends, Body, HTTPException
from typing import List, Optional
import logging

from app.handlers.delete_handler import DeleteHandler
from app.schemas.delete_schema import DeleteRequest, DeleteResponse, BatchDeleteRequest, BatchDeleteResponse
from app.services.asset_service import AssetService
from app.services.transaction_service import TransactionService
from app.repositories.asset_repo import AssetRepository
from app.repositories.transaction_repo import TransactionRepository
from app.database import get_db_client

# Setup router
router = APIRouter(
    prefix="/delete",
    tags=["Delete"],
    responses={404: {"description": "Not found"}},
)

logger = logging.getLogger(__name__)

def get_delete_handler(db_client=Depends(get_db_client)) -> DeleteHandler:
    """Dependency to get the delete handler with all required dependencies."""
    asset_repo = AssetRepository(db_client)
    transaction_repo = TransactionRepository(db_client)
    
    asset_service = AssetService(asset_repo)
    transaction_service = TransactionService(transaction_repo)
    
    return DeleteHandler(
        asset_service=asset_service,
        transaction_service=transaction_service
    )

@router.post("", response_model=DeleteResponse)
async def delete_asset(
    delete_request: DeleteRequest = Body(...),
    delete_handler: DeleteHandler = Depends(get_delete_handler)
) -> DeleteResponse:
    """
    Delete an asset.
    
    Performs a soft delete, marking the asset as deleted without removing it from the database.
    Only the asset owner can delete their assets.
    
    Args:
        delete_request: Request containing asset ID and wallet address
        
    Returns:
        DeleteResponse containing deletion result
    """
    result = await delete_handler.delete_asset(
        asset_id=delete_request.asset_id,
        wallet_address=delete_request.wallet_address,
        reason=delete_request.reason
    )
    return result

@router.post("/batch", response_model=BatchDeleteResponse)
async def batch_delete_assets(
    batch_request: BatchDeleteRequest = Body(...),
    delete_handler: DeleteHandler = Depends(get_delete_handler)
) -> BatchDeleteResponse:
    """
    Delete multiple assets in a batch operation.
    
    Performs soft deletes, marking assets as deleted without removing them from the database.
    Only the asset owner can delete their assets.
    
    Args:
        batch_request: Request containing list of asset IDs and wallet address
        
    Returns:
        BatchDeleteResponse containing batch deletion results
    """
    result = await delete_handler.batch_delete_assets(
        asset_ids=batch_request.asset_ids,
        wallet_address=batch_request.wallet_address,
        reason=batch_request.reason
    )
    return result

@router.delete("/asset/{asset_id}", response_model=DeleteResponse)
async def delete_asset_by_path(
    asset_id: str,
    wallet_address: str,
    reason: Optional[str] = None,
    delete_handler: DeleteHandler = Depends(get_delete_handler)
) -> DeleteResponse:
    """
    Delete an asset using path parameters.
    
    Alternative endpoint that uses path parameters instead of request body.
    Performs a soft delete, marking the asset as deleted without removing it from the database.
    
    Args:
        asset_id: The ID of the asset to delete
        wallet_address: The wallet address performing the deletion
        reason: Optional reason for deletion
        
    Returns:
        DeleteResponse containing deletion result
    """
    result = await delete_handler.delete_asset(
        asset_id=asset_id,
        wallet_address=wallet_address,
        reason=reason
    )
    return result
