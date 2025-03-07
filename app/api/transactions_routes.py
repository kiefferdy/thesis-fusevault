from fastapi import APIRouter, Depends, Query
from typing import Dict, Any, Optional, List
import logging

from app.handlers.transaction_handler import TransactionHandler
from app.services.transaction_service import TransactionService
from app.services.asset_service import AssetService
from app.repositories.transaction_repo import TransactionRepository
from app.repositories.asset_repo import AssetRepository
from app.database import get_db_client

# Setup router
router = APIRouter(
    prefix="/transactions",
    tags=["Transactions"],
    responses={404: {"description": "Not found"}},
)

logger = logging.getLogger(__name__)

def get_transaction_handler(db_client=Depends(get_db_client)) -> TransactionHandler:
    """Dependency to get the transaction handler with all required dependencies."""
    transaction_repo = TransactionRepository(db_client)
    asset_repo = AssetRepository(db_client)
    
    transaction_service = TransactionService(transaction_repo)
    asset_service = AssetService(asset_repo)
    
    return TransactionHandler(transaction_service, asset_service)

@router.get("/asset/{asset_id}", response_model=Dict[str, Any])
async def get_asset_history(
    asset_id: str,
    version: Optional[int] = None,
    transaction_handler: TransactionHandler = Depends(get_transaction_handler)
) -> Dict[str, Any]:
    """
    Get transaction history for a specific asset.
    
    Args:
        asset_id: The asset ID to get history for
        version: Optional specific version to filter by
        
    Returns:
        Dict containing transaction history for the asset
    """
    return await transaction_handler.get_asset_history(asset_id, version)

@router.get("/wallet/{wallet_address}", response_model=Dict[str, Any])
async def get_wallet_history(
    wallet_address: str,
    include_all_versions: bool = False,
    transaction_handler: TransactionHandler = Depends(get_transaction_handler)
) -> Dict[str, Any]:
    """
    Get transaction history for a specific wallet.
    
    Args:
        wallet_address: The wallet address to get history for
        include_all_versions: Whether to include all versions or just current ones
        
    Returns:
        Dict containing transaction history for the wallet
    """
    return await transaction_handler.get_wallet_history(wallet_address, include_all_versions)

@router.get("/{transaction_id}", response_model=Dict[str, Any])
async def get_transaction_details(
    transaction_id: str,
    transaction_handler: TransactionHandler = Depends(get_transaction_handler)
) -> Dict[str, Any]:
    """
    Get details for a specific transaction.
    
    Args:
        transaction_id: The ID of the transaction to get details for
        
    Returns:
        Dict containing transaction details
    """
    return await transaction_handler.get_transaction_details(transaction_id)

@router.post("", response_model=Dict[str, Any])
async def record_transaction(
    asset_id: str,
    action: str,
    wallet_address: str,
    metadata: Optional[Dict[str, Any]] = None,
    transaction_handler: TransactionHandler = Depends(get_transaction_handler)
) -> Dict[str, Any]:
    """
    Record a new transaction.
    
    Args:
        asset_id: The asset ID involved in the transaction
        action: The type of action (CREATE, UPDATE, VERSION_CREATE, etc.)
        wallet_address: The wallet address performing the action
        metadata: Optional additional transaction metadata
        
    Returns:
        Dict containing information about the recorded transaction
    """
    return await transaction_handler.record_transaction(
        asset_id=asset_id,
        action=action,
        wallet_address=wallet_address,
        metadata=metadata
    )

@router.get("/summary/{wallet_address}", response_model=Dict[str, Any])
async def get_transaction_summary(
    wallet_address: str,
    transaction_handler: TransactionHandler = Depends(get_transaction_handler)
) -> Dict[str, Any]:
    """
    Get a summary of transactions for a wallet address.
    
    Args:
        wallet_address: The wallet address to get summary for
        
    Returns:
        Dict containing transaction summary information
    """
    return await transaction_handler.get_transaction_summary(wallet_address)
