from fastapi import APIRouter, Depends, HTTPException, Request
from typing import Dict, Any, Optional
from pydantic import BaseModel
import logging

from app.services.blockchain_service import BlockchainService
from app.utilities.auth_middleware import get_current_user, get_wallet_address
from app.config import settings

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/delegation", tags=["Delegation"])


class DelegationStatusResponse(BaseModel):
    is_delegated: bool
    server_wallet_address: str
    user_wallet_address: str
    can_update_assets: bool
    can_delete_assets: bool


class SetDelegationRequest(BaseModel):
    delegate_address: str
    status: bool


class ServerInfoResponse(BaseModel):
    server_wallet_address: str
    network: Dict[str, Any]
    features: Dict[str, Any]


def get_blockchain_service() -> BlockchainService:
    """Dependency to get the blockchain service."""
    return BlockchainService()


@router.get("/server-info", response_model=ServerInfoResponse)
async def get_server_info():
    """
    Get server configuration including the server wallet address.
    This endpoint is public to allow frontend to display delegation info before auth.
    """
    return ServerInfoResponse(
        server_wallet_address=settings.wallet_address,
        network={
            "chain_id": 11155111,  # Sepolia
            "network_name": "Sepolia Testnet",
            "rpc_url": "https://sepolia.etherscan.io"
        },
        features={
            "api_keys_enabled": settings.api_key_auth_enabled,
            "max_api_keys_per_wallet": settings.api_key_max_per_wallet if settings.api_key_auth_enabled else 0,
            "delegation_required_for_api_keys": True
        }
    )


@router.get("/status", response_model=DelegationStatusResponse)
async def check_delegation_status(
    wallet_address: str = Depends(get_wallet_address),
    blockchain_service: BlockchainService = Depends(get_blockchain_service)
):
    """
    Check if the current user has delegated the server wallet.
    
    Returns:
        Delegation status including what operations are allowed
    """
    try:
        # Check delegation status on blockchain
        is_delegated = await blockchain_service.check_delegation(
            owner_address=wallet_address,
            delegate_address=settings.wallet_address
        )
        
        return DelegationStatusResponse(
            is_delegated=is_delegated,
            server_wallet_address=settings.wallet_address,
            user_wallet_address=wallet_address,
            can_update_assets=is_delegated,
            can_delete_assets=is_delegated
        )
        
    except Exception as e:
        logger.error(f"Error checking delegation status: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to check delegation status: {str(e)}"
        )


@router.post("/set")
async def set_delegation(
    delegation_request: SetDelegationRequest,
    request: Request,
    wallet_address: str = Depends(get_wallet_address),
    blockchain_service: BlockchainService = Depends(get_blockchain_service)
):
    """
    Prepare a transaction to set delegation status.
    
    This returns an unsigned transaction that the frontend must sign and broadcast.
    Only wallet-authenticated users can use this endpoint.
    """
    # Check if this is wallet auth
    auth_context = getattr(request.state, "auth_context", {})
    if auth_context.get("auth_method") != "wallet":
        raise HTTPException(
            status_code=403,
            detail="This endpoint requires wallet authentication"
        )
    
    try:
        # Validate delegate address
        if delegation_request.delegate_address.lower() != settings.wallet_address.lower():
            raise HTTPException(
                status_code=400,
                detail=f"Invalid delegate address. Expected server wallet: {settings.wallet_address}"
            )
        
        # Build unsigned transaction for setting delegation
        result = await blockchain_service.transaction_builder.build_set_delegate_transaction(
            delegate_address=delegation_request.delegate_address,
            status=delegation_request.status,
            from_address=wallet_address
        )
        
        if not result.get("success"):
            raise HTTPException(
                status_code=500,
                detail=result.get("error", "Failed to prepare delegation transaction")
            )
        
        logger.info(
            f"Prepared delegation transaction for {wallet_address} -> "
            f"{delegation_request.delegate_address} (status: {delegation_request.status})"
        )
        
        return {
            "success": True,
            "transaction": result.get("transaction"),
            "estimated_gas": result.get("estimated_gas"),
            "gas_price": result.get("gas_price"),
            "action": "setDelegate",
            "delegate_address": delegation_request.delegate_address,
            "status": delegation_request.status
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error preparing delegation transaction: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to prepare delegation transaction: {str(e)}"
        )


@router.get("/check/{owner_address}/{delegate_address}")
async def check_specific_delegation(
    owner_address: str,
    delegate_address: str,
    blockchain_service: BlockchainService = Depends(get_blockchain_service),
    _: Dict[str, Any] = Depends(get_current_user)
):
    """
    Check if a specific delegation exists between two addresses.
    
    Args:
        owner_address: The address that would grant delegation
        delegate_address: The address that would receive delegation
        
    Returns:
        Delegation status
    """
    try:
        is_delegated = await blockchain_service.check_delegation(
            owner_address=owner_address,
            delegate_address=delegate_address
        )
        
        return {
            "owner_address": owner_address,
            "delegate_address": delegate_address,
            "is_delegated": is_delegated
        }
        
    except Exception as e:
        logger.error(f"Error checking specific delegation: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to check delegation: {str(e)}"
        )