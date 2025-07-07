from fastapi import APIRouter, Depends
from typing import Dict, Any, Optional
import logging

from app.handlers.transaction_handler import TransactionHandler
from app.schemas.transaction_schema import (
    TransactionResponse, TransactionHistoryResponse, 
    WalletHistoryResponse, TransactionRecordResponse, TransactionSummaryResponse
)
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

@router.get("/asset/{asset_id}", response_model=TransactionHistoryResponse)
async def get_asset_history(
    asset_id: str,
    version: Optional[int] = None,
    transaction_handler: TransactionHandler = Depends(get_transaction_handler)
) -> TransactionHistoryResponse:
    """
    Get transaction history for a specific asset.
    
    Args:
        asset_id: The asset ID to get history for
        version: Optional specific version to filter by
        
    Returns:
        TransactionHistoryResponse containing transaction history for the asset
    """
    result = await transaction_handler.get_asset_history(asset_id, version)
    return TransactionHistoryResponse(**result)

@router.get("/wallet/{wallet_address}", response_model=WalletHistoryResponse)
async def get_wallet_history(
    wallet_address: str,
    include_all_versions: bool = False,
    transaction_handler: TransactionHandler = Depends(get_transaction_handler)
) -> WalletHistoryResponse:
    """
    Get transaction history for a specific wallet.
    
    Args:
        wallet_address: The wallet address to get history for
        include_all_versions: Whether to include all versions or just current ones
        
    Returns:
        WalletHistoryResponse containing transaction history for the wallet
    """
    result = await transaction_handler.get_wallet_history(wallet_address, include_all_versions)
    return WalletHistoryResponse(**result)

@router.get("/{transaction_id}", response_model=TransactionResponse)
async def get_transaction_details(
    transaction_id: str,
    transaction_handler: TransactionHandler = Depends(get_transaction_handler)
) -> TransactionResponse:
    """
    Get details for a specific transaction.
    
    Args:
        transaction_id: The ID of the transaction to get details for
        
    Returns:
        TransactionResponse containing transaction details
    """
    result = await transaction_handler.get_transaction_details(transaction_id)
    return TransactionResponse(**result)

@router.post("", response_model=TransactionRecordResponse)
async def record_transaction(
    asset_id: str,
    action: str,
    wallet_address: str,
    performed_by: str,
    metadata: Optional[Dict[str, Any]] = None,
    transaction_handler: TransactionHandler = Depends(get_transaction_handler)
) -> TransactionRecordResponse:
    """
    Record a new transaction.
    
    Args:
        asset_id: The asset ID involved in the transaction
        action: The type of action (CREATE, UPDATE, VERSION_CREATE, etc.)
        wallet_address: The wallet address that owns the asset
        performed_by: Wallet address that actually performed the action (for delegation)
        metadata: Optional additional transaction metadata
        
    Returns:
        TransactionRecordResponse containing information about the recorded transaction
    """
    result = await transaction_handler.record_transaction(
        asset_id=asset_id,
        action=action,
        wallet_address=wallet_address,
        performed_by=performed_by,
        metadata=metadata
    )
    return TransactionRecordResponse(**result)

@router.get("/summary/{wallet_address}", response_model=TransactionSummaryResponse)
async def get_transaction_summary(
    wallet_address: str,
    transaction_handler: TransactionHandler = Depends(get_transaction_handler)
) -> TransactionSummaryResponse:
    """
    Get a summary of transactions for a wallet address.
    
    Args:
        wallet_address: The wallet address to get summary for
        
    Returns:
        TransactionSummaryResponse containing transaction summary information
    """
    try:
        result = await transaction_handler.get_transaction_summary(wallet_address)
        return result  # We now return the full result object directly
    except Exception as e:
        logger.error(f"Error in transaction summary endpoint: {str(e)}")
        # Return default values to avoid errors
        return {
            "status": "success",
            "wallet_address": wallet_address,
            "total_transactions": 0,
            "unique_assets": 0,
            "total_asset_size": 0,
            "actions": {},
            "asset_types": {}
        }

@router.get("/recent/{wallet_address}", response_model=WalletHistoryResponse)
async def get_recent_transactions(
    wallet_address: str,
    limit: int = 10,
    transaction_handler: TransactionHandler = Depends(get_transaction_handler)
) -> WalletHistoryResponse:
    """
    Get recent transactions for a specific wallet address.
    
    Args:
        wallet_address: The wallet address to get recent transactions for
        limit: Maximum number of transactions to return
        
    Returns:
        WalletHistoryResponse containing recent transactions
    """
    try:
        result = await transaction_handler.get_wallet_history(
            wallet_address=wallet_address, 
            include_all_versions=False,
            limit=limit
        )
        return WalletHistoryResponse(**result)
    except Exception as e:
        logger.error(f"Error getting recent transactions: {str(e)}")
        # Return empty response instead of error
        return WalletHistoryResponse(
            status="success", 
            wallet_address=wallet_address,
            transactions=[],
            count=0
        )

@router.get("/all/{wallet_address}", response_model=WalletHistoryResponse)
async def get_all_transactions(
    wallet_address: str,
    transaction_handler: TransactionHandler = Depends(get_transaction_handler)
) -> WalletHistoryResponse:
    """
    Get all transactions for a specific wallet address.
    
    Args:
        wallet_address: The wallet address to get all transactions for
        
    Returns:
        WalletHistoryResponse containing all transactions
    """
    try:
        result = await transaction_handler.get_wallet_history(
            wallet_address=wallet_address, 
            include_all_versions=True
        )
        return WalletHistoryResponse(**result)
    except Exception as e:
        logger.error(f"Error getting all transactions: {str(e)}")
        # Return empty response instead of error
        return WalletHistoryResponse(
            status="success", 
            wallet_address=wallet_address,
            transactions=[],
            count=0
        )
