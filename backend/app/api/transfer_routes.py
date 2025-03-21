from fastapi import APIRouter, Depends, Body, HTTPException, Request
from typing import Optional, Dict, Any
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
from app.repositories.auth_repo import AuthRepository
from app.services.auth_service import AuthService
from app.database import get_db_client
from app.utilities.auth_middleware import get_current_user, get_wallet_address

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
    transfer_handler: TransferHandler = Depends(get_transfer_handler),
    current_user: Dict[str, Any] = Depends(get_current_user)
) -> TransferInitiateResponse:
    """
    Initiate a transfer of an asset to a new owner.
    User must be authenticated to use this endpoint.
    
    Args:
        transfer_request: Request containing asset ID, current owner, and new owner
        transfer_handler: The transfer handler
        current_user: The authenticated user data
        
    Returns:
        TransferInitiateResponse containing initiation result
    """
    # Verify that the authenticated user is the current owner initiating the transfer
    authenticated_wallet = current_user.get("walletAddress")
    if authenticated_wallet.lower() != transfer_request.current_owner.lower():
        logger.warning(f"Unauthorized transfer initiation attempt: {authenticated_wallet} tried to transfer asset owned by {transfer_request.current_owner}")
        raise HTTPException(
            status_code=403,
            detail="You can only initiate transfers for assets you own"
        )
        
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
    transfer_handler: TransferHandler = Depends(get_transfer_handler),
    current_user: Dict[str, Any] = Depends(get_current_user)
) -> TransferAcceptResponse:
    """
    Accept a transfer of an asset from a previous owner.
    User must be authenticated to use this endpoint.
    
    Args:
        transfer_request: Request containing asset ID, previous owner, and new owner
        transfer_handler: The transfer handler
        current_user: The authenticated user data
        
    Returns:
        TransferAcceptResponse containing acceptance result
    """
    # Verify that the authenticated user is the new owner accepting the transfer
    authenticated_wallet = current_user.get("walletAddress")
    if authenticated_wallet.lower() != transfer_request.new_owner.lower():
        logger.warning(f"Unauthorized transfer acceptance attempt: {authenticated_wallet} tried to accept transfer intended for {transfer_request.new_owner}")
        raise HTTPException(
            status_code=403,
            detail="You can only accept transfers intended for your wallet address"
        )
        
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
    transfer_handler: TransferHandler = Depends(get_transfer_handler),
    current_user: Dict[str, Any] = Depends(get_current_user)
) -> TransferCancelResponse:
    """
    Cancel a pending transfer.
    User must be authenticated to use this endpoint.
    
    Args:
        transfer_request: Request containing asset ID and current owner
        transfer_handler: The transfer handler
        current_user: The authenticated user data
        
    Returns:
        TransferCancelResponse containing cancellation result
    """
    # Verify that the authenticated user is the current owner canceling the transfer
    authenticated_wallet = current_user.get("walletAddress")
    if authenticated_wallet.lower() != transfer_request.current_owner.lower():
        logger.warning(f"Unauthorized transfer cancellation attempt: {authenticated_wallet} tried to cancel transfer for asset owned by {transfer_request.current_owner}")
        raise HTTPException(
            status_code=403,
            detail="You can only cancel transfers for assets you own"
        )
        
    result = await transfer_handler.cancel_transfer(
        asset_id=transfer_request.asset_id,
        current_owner=transfer_request.current_owner,
        notes=transfer_request.notes
    )
    return TransferCancelResponse(**result)

@router.get("/pending/{wallet_address}", response_model=PendingTransfersResponse)
async def get_pending_transfers(
    wallet_address: str,
    request: Request,
    transfer_handler: TransferHandler = Depends(get_transfer_handler)
) -> PendingTransfersResponse:
    """
    Get all pending transfers for a wallet address.
    This is a read operation that can work in both authenticated and demo modes.
    
    Args:
        wallet_address: The wallet address to get pending transfers for
        request: The request object
        transfer_handler: The transfer handler
        
    Returns:
        PendingTransfersResponse containing lists of pending transfers
    """
    # Check if authenticated
    is_authenticated = hasattr(request.state, "user") and request.state.user is not None
    
    if is_authenticated:
        # If authenticated, verify that the user is requesting their own pending transfers
        authenticated_wallet = request.state.user.get("walletAddress")
        if authenticated_wallet.lower() != wallet_address.lower():
            logger.warning(f"User {authenticated_wallet} attempted to access pending transfers for {wallet_address}")
            # Return empty results instead of error for privacy
            return PendingTransfersResponse(
                status="success",
                initiated_transfers=[],
                pending_transfers=[]
            )
    
    result = await transfer_handler.get_pending_transfers(wallet_address)
    return PendingTransfersResponse(**result)
