from fastapi import APIRouter, Depends, Body
from typing import Optional
import logging

from app.handlers.transfer_handler import TransferHandler
from app.schemas.transfer_schema import (
    TransferInitiateRequest, TransferInitiateResponse, 
    TransferAcceptRequest, TransferAcceptResponse,
    TransferCancelRequest, TransferCancelResponse,
    PendingTransfersResponse
)
from app.services.asset_service import AssetService
from app.services.blockchain_service import BlockchainService
from app.services.transaction_service import TransactionService
from app.repositories.asset_repo import AssetRepository
from app.repositories.transaction_repo import TransactionRepository
from app.database import get_db_client

# Setup router
router = APIRouter(
    prefix="/transfers",
    tags=["Transfers"],
    responses={404: {"description": "Not found"}},
)

logger = logging.getLogger(__name__)

def get_transfer_handler(db_client=Depends(get_db_client)) -> TransferHandler:
    """Dependency to get the transfer handler with all required dependencies."""
    asset_repo = AssetRepository(db_client)
    transaction_repo = TransactionRepository(db_client)
    
    asset_service = AssetService(asset_repo)
    blockchain_service = BlockchainService()
    transaction_service = TransactionService(transaction_repo)
    
    return TransferHandler(
        asset_service=asset_service,
        blockchain_service=blockchain_service,
        transaction_service=transaction_service
    )

@router.post("/initiate", response_model=TransferInitiateResponse)
async def initiate_transfer(
    transfer_request: TransferInitiateRequest = Body(...),
    transfer_handler: TransferHandler = Depends(get_transfer_handler)
) -> TransferInitiateResponse:
    """
    Initiate a transfer of an asset to a new owner.
    
    Args:
        transfer_request: Request containing asset ID, current owner, and new owner
        
    Returns:
        TransferInitiateResponse containing initiation result
    """
    result = await transfer_handler.initiate_transfer(
        asset_id=transfer_request.asset_id,
        current_owner=transfer_request.current_owner,
        new_owner=transfer_request.new_owner,
        notes=transfer_request.notes
    )
    return TransferInitiateResponse(**result)

@router.post("/accept", response_model=TransferAcceptResponse)
async def accept_transfer(
    transfer_request: TransferAcceptRequest = Body(...),
    transfer_handler: TransferHandler = Depends(get_transfer_handler)
) -> TransferAcceptResponse:
    """
    Accept a transfer of an asset from a previous owner.
    
    Args:
        transfer_request: Request containing asset ID, previous owner, and new owner
        
    Returns:
        TransferAcceptResponse containing acceptance result
    """
    result = await transfer_handler.accept_transfer(
        asset_id=transfer_request.asset_id,
        previous_owner=transfer_request.previous_owner,
        new_owner=transfer_request.new_owner,
        notes=transfer_request.notes
    )
    return TransferAcceptResponse(**result)

@router.post("/cancel", response_model=TransferCancelResponse)
async def cancel_transfer(
    transfer_request: TransferCancelRequest = Body(...),
    transfer_handler: TransferHandler = Depends(get_transfer_handler)
) -> TransferCancelResponse:
    """
    Cancel a pending transfer.
    
    Args:
        transfer_request: Request containing asset ID and current owner
        
    Returns:
        TransferCancelResponse containing cancellation result
    """
    result = await transfer_handler.cancel_transfer(
        asset_id=transfer_request.asset_id,
        current_owner=transfer_request.current_owner,
        notes=transfer_request.notes
    )
    return TransferCancelResponse(**result)

@router.get("/pending/{wallet_address}", response_model=PendingTransfersResponse)
async def get_pending_transfers(
    wallet_address: str,
    transfer_handler: TransferHandler = Depends(get_transfer_handler)
) -> PendingTransfersResponse:
    """
    Get all pending transfers for a wallet address.
    
    Args:
        wallet_address: The wallet address to get pending transfers for
        
    Returns:
        PendingTransfersResponse containing lists of pending transfers
    """
    result = await transfer_handler.get_pending_transfers(wallet_address)
    return PendingTransfersResponse(**result)
