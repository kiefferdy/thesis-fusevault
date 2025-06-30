from fastapi import APIRouter, Depends, HTTPException, Request, Query
from typing import Dict, Any, Optional, List
from pydantic import BaseModel
import logging

from app.services.blockchain_service import BlockchainService
from app.services.user_service import UserService
from app.services.asset_service import AssetService
from app.repositories.user_repo import UserRepository
from app.repositories.asset_repo import AssetRepository
from app.utilities.auth_middleware import get_current_user, get_wallet_address
from app.database import get_db_client
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


# New models for user delegation
class UserSearchResponse(BaseModel):
    users: List[Dict[str, Any]]
    total: int
    query: str


class UserDelegationRequest(BaseModel):
    delegate_address: str
    status: bool


class UserDelegationResponse(BaseModel):
    owner_address: str
    delegate_address: str
    is_delegated: bool
    transaction_data: Optional[Dict[str, Any]] = None


class DelegateListResponse(BaseModel):
    delegates: List[Dict[str, Any]]
    count: int


class DelegatedAssetsResponse(BaseModel):
    owner_address: str
    owner_username: Optional[str]
    assets: List[Dict[str, Any]]
    total_assets: int


def get_blockchain_service() -> BlockchainService:
    """Dependency to get the blockchain service."""
    return BlockchainService()


def get_user_service(db_client=Depends(get_db_client)) -> UserService:
    """Dependency to get the user service."""
    user_repo = UserRepository(db_client)
    return UserService(user_repo)


def get_asset_service(db_client=Depends(get_db_client)) -> AssetService:
    """Dependency to get the asset service."""
    asset_repo = AssetRepository(db_client)
    return AssetService(asset_repo)


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


# User-to-User Delegation Endpoints

@router.get("/users/search", response_model=UserSearchResponse)
async def search_users(
    q: str = Query(..., description="Search query (wallet address or username)"),
    limit: int = Query(10, description="Maximum number of results"),
    current_user: Dict[str, Any] = Depends(get_current_user),
    user_service: UserService = Depends(get_user_service)
):
    """
    Search for users by wallet address or username.
    
    Args:
        q: Search query (partial wallet address or username)
        limit: Maximum number of results to return
        
    Returns:
        UserSearchResponse with matching users
    """
    try:
        # Search users using the user service
        users = await user_service.search_users(q, limit + 1)  # Get one extra to filter out current user
        
        # Filter out current user from results
        current_wallet = current_user.get("walletAddress", "").lower()
        filtered_users = [user for user in users if user.get("wallet_address", "").lower() != current_wallet]
        
        return UserSearchResponse(
            users=filtered_users[:limit],
            total=len(filtered_users),
            query=q
        )
        
    except Exception as e:
        logger.error(f"Error searching users: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to search users: {str(e)}"
        )


@router.post("/users/delegate", response_model=UserDelegationResponse)
async def set_user_delegation(
    delegation_request: UserDelegationRequest,
    request: Request,
    wallet_address: str = Depends(get_wallet_address),
    blockchain_service: BlockchainService = Depends(get_blockchain_service),
    user_service: UserService = Depends(get_user_service)
):
    """
    Prepare a transaction to set user delegation status.
    
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
        # Validate that delegate address is a real user
        delegate_user = await user_service.get_user(delegation_request.delegate_address)
        if not delegate_user or delegate_user.get("status") != "success":
            raise HTTPException(
                status_code=400,
                detail="Delegate address is not a registered FuseVault user"
            )
        
        # Cannot delegate to yourself
        if delegation_request.delegate_address.lower() == wallet_address.lower():
            raise HTTPException(
                status_code=400,
                detail="Cannot delegate to yourself"
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
            f"Prepared user delegation transaction for {wallet_address} -> "
            f"{delegation_request.delegate_address} (status: {delegation_request.status})"
        )
        
        return UserDelegationResponse(
            owner_address=wallet_address,
            delegate_address=delegation_request.delegate_address,
            is_delegated=delegation_request.status,
            transaction_data={
                "transaction": result.get("transaction"),
                "estimated_gas": result.get("estimated_gas"),
                "gas_price": result.get("gas_price"),
                "action": "setDelegate"
            }
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error preparing user delegation transaction: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to prepare user delegation transaction: {str(e)}"
        )


@router.get("/users/my-delegates", response_model=DelegateListResponse)
async def get_my_delegates(
    wallet_address: str = Depends(get_wallet_address),
    blockchain_service: BlockchainService = Depends(get_blockchain_service),
    user_service: UserService = Depends(get_user_service)
):
    """
    Get list of users I have set as delegates.
    
    Returns:
        DelegateListResponse with list of delegates
    """
    try:
        # This would require tracking delegations in the database or querying the blockchain
        # For now, return empty list - would need to be implemented properly
        delegates = []
        
        return DelegateListResponse(
            delegates=delegates,
            count=len(delegates)
        )
        
    except Exception as e:
        logger.error(f"Error getting delegates: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get delegates: {str(e)}"
        )


@router.get("/users/delegated-to-me", response_model=DelegateListResponse)
async def get_delegated_to_me(
    wallet_address: str = Depends(get_wallet_address),
    blockchain_service: BlockchainService = Depends(get_blockchain_service),
    user_service: UserService = Depends(get_user_service)
):
    """
    Get list of users who have set me as delegate.
    
    Returns:
        DelegateListResponse with list of users who delegated to me
    """
    try:
        # This would require tracking delegations in the database or querying the blockchain
        # For now, return empty list - would need to be implemented properly
        delegators = []
        
        return DelegateListResponse(
            delegates=delegators,
            count=len(delegators)
        )
        
    except Exception as e:
        logger.error(f"Error getting delegators: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get delegators: {str(e)}"
        )


@router.delete("/users/delegate/{delegate_address}")
async def revoke_user_delegation(
    delegate_address: str,
    request: Request,
    wallet_address: str = Depends(get_wallet_address),
    blockchain_service: BlockchainService = Depends(get_blockchain_service)
):
    """
    Prepare a transaction to revoke user delegation.
    
    This returns an unsigned transaction that the frontend must sign and broadcast.
    """
    # Check if this is wallet auth
    auth_context = getattr(request.state, "auth_context", {})
    if auth_context.get("auth_method") != "wallet":
        raise HTTPException(
            status_code=403,
            detail="This endpoint requires wallet authentication"
        )
    
    try:
        # Build unsigned transaction for revoking delegation
        result = await blockchain_service.transaction_builder.build_set_delegate_transaction(
            delegate_address=delegate_address,
            status=False,  # Revoke delegation
            from_address=wallet_address
        )
        
        if not result.get("success"):
            raise HTTPException(
                status_code=500,
                detail=result.get("error", "Failed to prepare revoke delegation transaction")
            )
        
        logger.info(
            f"Prepared revoke delegation transaction for {wallet_address} -> {delegate_address}"
        )
        
        return UserDelegationResponse(
            owner_address=wallet_address,
            delegate_address=delegate_address,
            is_delegated=False,
            transaction_data={
                "transaction": result.get("transaction"),
                "estimated_gas": result.get("estimated_gas"),
                "gas_price": result.get("gas_price"),
                "action": "setDelegate"
            }
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error preparing revoke delegation transaction: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to prepare revoke delegation transaction: {str(e)}"
        )


@router.get("/users/{owner_address}/assets", response_model=DelegatedAssetsResponse)
async def get_delegated_assets(
    owner_address: str,
    wallet_address: str = Depends(get_wallet_address),
    blockchain_service: BlockchainService = Depends(get_blockchain_service),
    user_service: UserService = Depends(get_user_service),
    asset_service: AssetService = Depends(get_asset_service)
):
    """
    Get assets of a user who has delegated to me.
    
    Args:
        owner_address: The address of the user who delegated to me
        
    Returns:
        DelegatedAssetsResponse with assets I can manage
    """
    try:
        # Check if owner has delegated to current user
        is_delegated = await blockchain_service.check_delegation(
            owner_address=owner_address,
            delegate_address=wallet_address
        )
        
        if not is_delegated:
            raise HTTPException(
                status_code=403,
                detail="You are not a delegate for this user"
            )
        
        # Get owner user info
        owner_user = await user_service.get_user(owner_address)
        owner_username = None
        if owner_user and owner_user.get("status") == "success":
            owner_username = owner_user["user"].get("username")
        
        # Get assets for the owner
        assets = await asset_service.get_user_assets(owner_address)
        
        return DelegatedAssetsResponse(
            owner_address=owner_address,
            owner_username=owner_username,
            assets=assets.get("assets", []),
            total_assets=len(assets.get("assets", []))
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting delegated assets: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get delegated assets: {str(e)}"
        )