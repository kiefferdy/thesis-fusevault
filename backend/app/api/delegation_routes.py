from fastapi import APIRouter, Depends, HTTPException, Request, Query
from typing import Dict, Any, Optional, List
from pydantic import BaseModel
import logging

from app.services.blockchain_service import BlockchainService
from app.services.user_service import UserService
from app.services.asset_service import AssetService
from app.services.transaction_service import TransactionService
from app.repositories.user_repo import UserRepository
from app.repositories.asset_repo import AssetRepository
from app.repositories.delegation_repo import DelegationRepository
from app.repositories.transaction_repo import TransactionRepository
from app.schemas.delegation_schema import (
    DelegationListResponse, 
    DelegationResponse,
    DelegationStatusResponse,
    SetDelegationRequest,
    ServerInfoResponse,
    UserSearchResponse,
    UserDelegationRequest,
    UserDelegationResponse,
    DelegateListResponse,
    DelegatedAssetsResponse,
    DelegationConfirmRequest,
    DelegationConfirmResponse,
    DelegationSyncRequest,
    DelegationSyncResponse
)
from app.utilities.auth_middleware import get_current_user, get_wallet_address, get_wallet_only_user
from app.database import get_db_client
from app.config import settings

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/delegation", tags=["Delegation"])


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


def get_transaction_service(db_client=Depends(get_db_client)) -> TransactionService:
    """Dependency to get the transaction service."""
    transaction_repo = TransactionRepository(db_client)
    return TransactionService(transaction_repo)


# Using simplified hybrid approach for delegation management


def get_delegation_repository(db_client=Depends(get_db_client)) -> DelegationRepository:
    """Dependency to get the delegation repository."""
    return DelegationRepository(db_client)


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
    _: Dict[str, Any] = Depends(get_wallet_only_user)
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

@router.post("/users/delegate/confirm", response_model=DelegationConfirmResponse)
async def confirm_user_delegation(
    confirm_request: DelegationConfirmRequest,
    request: Request,
    wallet_address: str = Depends(get_wallet_address),
    blockchain_service: BlockchainService = Depends(get_blockchain_service),
    delegation_repo: DelegationRepository = Depends(get_delegation_repository)
):
    """
    Confirm delegation after successful MetaMask transaction.
    
    This endpoint verifies the transaction succeeded on-chain and immediately
    updates the database for instant UI feedback.
    
    Args:
        confirm_request: Transaction details and delegation info
        
    Returns:
        DelegationConfirmResponse with success status and delegation ID
    """
    # Check if this is wallet auth
    auth_context = getattr(request.state, "auth_context", {})
    if auth_context.get("auth_method") != "wallet":
        raise HTTPException(
            status_code=403,
            detail="This endpoint requires wallet authentication"
        )
    
    try:
        # Verify owner address matches authenticated wallet
        if confirm_request.owner_address.lower() != wallet_address.lower():
            raise HTTPException(
                status_code=403,
                detail="Owner address must match authenticated wallet"
            )
        
        # Verify transaction exists and succeeded using existing blockchain service
        logger.info(f"Verifying transaction {confirm_request.transaction_hash}")
        
        try:
            verification_result = await blockchain_service.verify_transaction_success(confirm_request.transaction_hash)
        except Exception as e:
            logger.error(f"Failed to verify transaction: {str(e)}")
            raise HTTPException(
                status_code=400,
                detail=f"Transaction verification failed: {str(e)}"
            )
        
        if not verification_result.get("success"):
            raise HTTPException(
                status_code=400,
                detail=verification_result.get("error", "Transaction failed on blockchain")
            )
        
        # Extract block number for database record
        block_number = verification_result.get("block_number")
        
        # Validate addresses
        try:
            from web3 import Web3
            owner_checksum = Web3.to_checksum_address(confirm_request.owner_address)
            delegate_checksum = Web3.to_checksum_address(confirm_request.delegate_address)
        except Exception:
            raise HTTPException(
                status_code=400,
                detail="Invalid wallet addresses provided"
            )
        
        # Create delegation data for database
        delegation_data = {
            "ownerAddress": confirm_request.owner_address.lower(),
            "delegateAddress": confirm_request.delegate_address.lower(),
            "isActive": confirm_request.status,
            "transactionHash": confirm_request.transaction_hash,
            "blockNumber": block_number
        }
        
        # Update database immediately
        delegation_id = await delegation_repo.upsert_delegation(delegation_data)
        
        logger.info(
            f"Delegation confirmed: {confirm_request.owner_address} -> "
            f"{confirm_request.delegate_address} = {confirm_request.status} "
            f"(TX: {confirm_request.transaction_hash}, ID: {delegation_id})"
        )
        
        action = "granted" if confirm_request.status else "revoked"
        return DelegationConfirmResponse(
            success=True,
            message=f"Delegation {action} successfully",
            delegation_id=delegation_id
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error confirming delegation: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to confirm delegation: {str(e)}"
        )


@router.post("/users/delegate/sync", response_model=DelegationSyncResponse)
async def sync_delegation_from_blockchain(
    sync_request: DelegationSyncRequest,
    wallet_address: str = Depends(get_wallet_address),
    blockchain_service: BlockchainService = Depends(get_blockchain_service),
    delegation_repo: DelegationRepository = Depends(get_delegation_repository)
):
    """
    Sync delegation state from blockchain to database when inconsistency is detected.
    
    This endpoint is called when frontend detects that delegation exists on blockchain
    but not in database (during pre-checks). It updates database to match blockchain state.
    
    Args:
        sync_request: Owner and delegate addresses to sync
        
    Returns:
        DelegationSyncResponse with sync status
    """
    try:
        # Verify owner address matches authenticated wallet
        if sync_request.owner_address.lower() != wallet_address.lower():
            raise HTTPException(
                status_code=403,
                detail="Owner address must match authenticated wallet"
            )
        
        logger.info(f"Syncing delegation state: {sync_request.owner_address} -> {sync_request.delegate_address}")
        
        # Check current blockchain state (source of truth)
        blockchain_status = await blockchain_service.check_delegation(
            owner_address=sync_request.owner_address,
            delegate_address=sync_request.delegate_address
        )
        
        # Check current database state
        existing_delegation = await delegation_repo.get_delegation(
            sync_request.owner_address, 
            sync_request.delegate_address
        )
        
        database_status = existing_delegation and existing_delegation.get("isActive", False)
        
        # Check if sync is needed (both directions)
        if blockchain_status == database_status:
            return DelegationSyncResponse(
                success=True,
                message=f"Database already in sync (both show {blockchain_status})",
                was_synced=False,
                delegation_id=existing_delegation.get("id") if existing_delegation else None
            )
        
        # Sync needed - update database to match blockchain
        delegation_data = {
            "ownerAddress": sync_request.owner_address.lower(),
            "delegateAddress": sync_request.delegate_address.lower(),
            "isActive": blockchain_status,
            # Note: No transaction hash available for externally created/revoked delegations
            # This is fine - the database record is just for UX optimization
        }
        
        delegation_id = await delegation_repo.upsert_delegation(delegation_data)
        
        action = "activated" if blockchain_status else "deactivated"
        logger.info(
            f"Delegation synced from blockchain: {sync_request.owner_address} -> "
            f"{sync_request.delegate_address} = {blockchain_status} ({action}, ID: {delegation_id})"
        )
        
        return DelegationSyncResponse(
            success=True,
            message=f"Delegation {action} to match blockchain state",
            was_synced=True,
            delegation_id=delegation_id
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error syncing delegation: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to sync delegation: {str(e)}"
        )


# Original delegation endpoints below...

@router.get("/users/search", response_model=UserSearchResponse)
async def search_users(
    q: str = Query(..., description="Search query (wallet address or username)"),
    limit: int = Query(10, description="Maximum number of results"),
    current_user: Dict[str, Any] = Depends(get_wallet_only_user),
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
        
        # Enrich search results with full profile information
        enriched_users = []
        for user in filtered_users[:limit]:
            # Get full user profile
            full_user = await user_service.get_user(user.get("wallet_address"))
            if full_user and full_user.get("status") == "success":
                user_data = full_user["user"]
                enriched_user = {
                    "id": user_data.get("id"),
                    "wallet_address": user_data.get("wallet_address"),
                    "username": user_data.get("username"),
                    "name": user_data.get("name"),
                    "organization": user_data.get("organization"),
                    "job_title": user_data.get("job_title"),
                    "bio": user_data.get("bio"),
                    "profile_image": user_data.get("profile_image"),
                    "location": user_data.get("location"),
                    "twitter": user_data.get("twitter"),
                    "linkedin": user_data.get("linkedin"),
                    "github": user_data.get("github"),
                    "created_at": user_data.get("created_at"),
                    "last_login": user_data.get("last_login")
                }
                enriched_users.append(enriched_user)
            else:
                # Fallback to basic user data if full profile not available
                enriched_users.append(user)
        
        return UserSearchResponse(
            users=enriched_users,
            total=len(enriched_users),
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
                "action": "setDelegate",
                "confirmation_endpoint": "/delegation/users/delegate/confirm",
                "instructions": "After MetaMask transaction succeeds, call the confirmation endpoint with transaction hash to update database immediately"
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


@router.get("/users/my-delegates", response_model=DelegationListResponse)
async def get_my_delegates(
    wallet_address: str = Depends(get_wallet_address),
    delegation_repo: DelegationRepository = Depends(get_delegation_repository),
    user_service: UserService = Depends(get_user_service)
):
    """
    Get list of users I have set as delegates.
    
    Returns:
        DelegationListResponse with list of delegates
    """
    try:
        # Get delegations from database
        delegations = await delegation_repo.get_delegations_by_owner(wallet_address, active_only=True)
        
        # Enrich with user information
        enriched_delegations = []
        for delegation in delegations:
            # Get delegate user info with full profile
            delegate_user = await user_service.get_user(delegation["delegateAddress"])
            delegate_data = {}
            if delegate_user and delegate_user.get("status") == "success":
                user_info = delegate_user["user"]
                delegate_data = {
                    "username": user_info.get("username"),
                    "name": user_info.get("name"),
                    "organization": user_info.get("organization"),
                    "job_title": user_info.get("job_title"),
                    "bio": user_info.get("bio"),
                    "profile_image": user_info.get("profile_image"),
                    "location": user_info.get("location"),
                    "twitter": user_info.get("twitter"),
                    "linkedin": user_info.get("linkedin"),
                    "github": user_info.get("github"),
                    "last_login": user_info.get("last_login"),
                    "created_at": user_info.get("created_at")
                }
            
            # Get owner user info (current user)
            owner_user = await user_service.get_user(wallet_address)
            owner_data = {}
            if owner_user and owner_user.get("status") == "success":
                user_info = owner_user["user"]
                owner_data = {
                    "username": user_info.get("username"),
                    "name": user_info.get("name")
                }
            
            # Create enriched delegation response
            enriched_delegation = DelegationResponse(
                id=delegation["id"],
                ownerAddress=delegation["ownerAddress"],
                delegateAddress=delegation["delegateAddress"],
                isActive=delegation["isActive"],
                ownerUsername=owner_data.get("username"),
                delegateUsername=delegate_data.get("username"),
                delegateName=delegate_data.get("name"),
                delegateOrganization=delegate_data.get("organization"),
                delegateJobTitle=delegate_data.get("job_title"),
                delegateBio=delegate_data.get("bio"),
                delegateProfileImage=delegate_data.get("profile_image"),
                delegateLocation=delegate_data.get("location"),
                delegateTwitter=delegate_data.get("twitter"),
                delegateLinkedin=delegate_data.get("linkedin"),
                delegateGithub=delegate_data.get("github"),
                delegateLastLogin=delegate_data.get("last_login"),
                delegateCreatedAt=delegate_data.get("created_at"),
                createdAt=delegation["createdAt"],
                updatedAt=delegation["updatedAt"],
                transactionHash=delegation.get("transactionHash"),
                blockNumber=delegation.get("blockNumber")
            )
            enriched_delegations.append(enriched_delegation)
        
        return DelegationListResponse(
            delegations=enriched_delegations,
            count=len(enriched_delegations),
            ownerAddress=wallet_address
        )
        
    except Exception as e:
        logger.error(f"Error getting delegates: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get delegates: {str(e)}"
        )


@router.get("/users/delegated-to-me", response_model=DelegationListResponse)
async def get_delegated_to_me(
    wallet_address: str = Depends(get_wallet_address),
    delegation_repo: DelegationRepository = Depends(get_delegation_repository),
    user_service: UserService = Depends(get_user_service)
):
    """
    Get list of users who have set me as delegate.
    
    Returns:
        DelegationListResponse with list of users who delegated to me
    """
    try:
        # Get delegations from database where current user is the delegate
        delegations = await delegation_repo.get_delegations_by_delegate(wallet_address, active_only=True)
        
        # Enrich with user information
        enriched_delegations = []
        for delegation in delegations:
            # Get owner user info with full profile
            owner_user = await user_service.get_user(delegation["ownerAddress"])
            owner_data = {}
            if owner_user and owner_user.get("status") == "success":
                user_info = owner_user["user"]
                owner_data = {
                    "username": user_info.get("username"),
                    "name": user_info.get("name"),
                    "organization": user_info.get("organization"),
                    "job_title": user_info.get("job_title"),
                    "bio": user_info.get("bio"),
                    "profile_image": user_info.get("profile_image"),
                    "location": user_info.get("location"),
                    "twitter": user_info.get("twitter"),
                    "linkedin": user_info.get("linkedin"),
                    "github": user_info.get("github"),
                    "last_login": user_info.get("last_login"),
                    "created_at": user_info.get("created_at")
                }
            
            # Get delegate user info (current user)
            delegate_user = await user_service.get_user(wallet_address)
            delegate_data = {}
            if delegate_user and delegate_user.get("status") == "success":
                user_info = delegate_user["user"]
                delegate_data = {
                    "username": user_info.get("username"),
                    "name": user_info.get("name")
                }
            
            # Create enriched delegation response
            enriched_delegation = DelegationResponse(
                id=delegation["id"],
                ownerAddress=delegation["ownerAddress"],
                delegateAddress=delegation["delegateAddress"],
                isActive=delegation["isActive"],
                ownerUsername=owner_data.get("username"),
                ownerName=owner_data.get("name"),
                ownerOrganization=owner_data.get("organization"),
                ownerJobTitle=owner_data.get("job_title"),
                ownerBio=owner_data.get("bio"),
                ownerProfileImage=owner_data.get("profile_image"),
                ownerLocation=owner_data.get("location"),
                ownerTwitter=owner_data.get("twitter"),
                ownerLinkedin=owner_data.get("linkedin"),
                ownerGithub=owner_data.get("github"),
                ownerLastLogin=owner_data.get("last_login"),
                ownerCreatedAt=owner_data.get("created_at"),
                delegateUsername=delegate_data.get("username"),
                createdAt=delegation["createdAt"],
                updatedAt=delegation["updatedAt"],
                transactionHash=delegation.get("transactionHash"),
                blockNumber=delegation.get("blockNumber")
            )
            enriched_delegations.append(enriched_delegation)
        
        return DelegationListResponse(
            delegations=enriched_delegations,
            count=len(enriched_delegations),
            delegateAddress=wallet_address
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
                "action": "setDelegate",
                "confirmation_endpoint": "/delegation/users/delegate/confirm",
                "instructions": "After MetaMask transaction succeeds, call the confirmation endpoint with transaction hash to update database immediately"
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


@router.get("/users/{owner_address}/assets/summary")
async def get_delegated_assets_summary(
    owner_address: str,
    wallet_address: str = Depends(get_wallet_address),
    blockchain_service: BlockchainService = Depends(get_blockchain_service),
    asset_service: AssetService = Depends(get_asset_service),
    transaction_service: TransactionService = Depends(get_transaction_service)
):
    """
    Get asset summary for a user who has delegated to me.
    Returns quick statistics and recent transactions for better UX.
    
    Args:
        owner_address: The address of the user who delegated to me
        
    Returns:
        Asset summary with counts and recent transactions
    """
    try:
        # SECURITY: Always check blockchain state (source of truth)
        is_delegated = await blockchain_service.check_delegation(
            owner_address=owner_address,
            delegate_address=wallet_address
        )
        
        if not is_delegated:
            raise HTTPException(
                status_code=403,
                detail="Access denied: delegation not found on blockchain"
            )
        
        # Get assets for the owner
        assets = await asset_service.get_user_assets(owner_address)
        
        # Get recent transactions for the owner
        try:
            recent_transactions = await transaction_service.get_wallet_history(
                wallet_address=owner_address,
                include_all_versions=False,
                limit=5  # Get last 5 transactions
            )
            
            # Enrich transactions with asset names
            enriched_transactions = []
            for transaction in recent_transactions:
                enriched_transaction = transaction.copy()
                asset_id = transaction.get('assetId')
                
                if asset_id:
                    try:
                        # Get asset metadata to extract name
                        asset_documents = await asset_service.get_user_assets(owner_address)
                        asset_name = None
                        
                        # Find the asset with matching ID
                        for asset_doc in asset_documents:
                            if asset_doc.get('assetId') == asset_id:
                                asset_name = asset_doc.get('criticalMetadata', {}).get('name') or asset_doc.get('nonCriticalMetadata', {}).get('name')
                                break
                        
                        # Add asset name to transaction
                        enriched_transaction['assetName'] = asset_name or asset_id
                        
                    except Exception as asset_error:
                        logger.warning(f"Failed to get asset name for {asset_id}: {str(asset_error)}")
                        enriched_transaction['assetName'] = asset_id
                else:
                    enriched_transaction['assetName'] = 'Unknown Asset'
                
                enriched_transactions.append(enriched_transaction)
            
            recent_transactions = enriched_transactions
            
        except Exception as e:
            logger.warning(f"Failed to fetch recent transactions for {owner_address}: {str(e)}")
            recent_transactions = []
        
        return {
            "owner_address": owner_address,
            "total_assets": len(assets),
            "recent_transactions": recent_transactions,
            "last_activity": assets[0].get("createdAt") if assets else None
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting delegated assets summary: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get delegated assets summary: {str(e)}"
        )


def categorize_content_type(content_type: str) -> str:
    """Categorize content type into broad categories for UI display."""
    if not content_type:
        return "unknown"
    
    content_type_lower = content_type.lower()
    
    if content_type_lower.startswith("image/"):
        return "images"
    elif content_type_lower.startswith("video/"):
        return "videos"
    elif content_type_lower.startswith("audio/"):
        return "audio"
    elif content_type_lower in ["application/pdf", "application/msword", "application/vnd.openxmlformats-officedocument.wordprocessingml.document"]:
        return "documents"
    elif content_type_lower.startswith("text/"):
        return "text"
    elif content_type_lower.startswith("application/"):
        return "applications"
    else:
        return "other"


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
    
    SECURITY: Always verifies delegation on blockchain regardless of database state.
    This ensures that even if database is inconsistent, access is properly controlled.
    
    Args:
        owner_address: The address of the user who delegated to me
        
    Returns:
        DelegatedAssetsResponse with assets I can manage
    """
    try:
        logger.info(f"Checking blockchain delegation: {owner_address} -> {wallet_address}")
        
        # SECURITY: Always check blockchain state (source of truth)
        is_delegated = await blockchain_service.check_delegation(
            owner_address=owner_address,
            delegate_address=wallet_address
        )
        
        if not is_delegated:
            logger.warning(f"Delegation access denied: {owner_address} has not delegated to {wallet_address}")
            raise HTTPException(
                status_code=403,
                detail="Access denied: delegation not found on blockchain"
            )
        
        logger.info(f"Delegation verified on blockchain: {owner_address} -> {wallet_address}")
        
        # Get owner user info
        owner_user = await user_service.get_user(owner_address)
        owner_username = None
        owner_name = None
        owner_profile_image = None
        owner_organization = None
        owner_job_title = None
        owner_bio = None
        owner_location = None
        
        if owner_user and owner_user.get("status") == "success":
            user_data = owner_user["user"]
            owner_username = user_data.get("username")
            owner_name = user_data.get("name")
            owner_profile_image = user_data.get("profileImage")
            owner_organization = user_data.get("organization")
            owner_job_title = user_data.get("jobTitle")
            owner_bio = user_data.get("bio")
            owner_location = user_data.get("location")
        
        # Get assets for the owner
        assets = await asset_service.get_user_assets(owner_address)
        
        return DelegatedAssetsResponse(
            owner_address=owner_address,
            owner_username=owner_username,
            owner_name=owner_name,
            owner_profile_image=owner_profile_image,
            owner_organization=owner_organization,
            owner_job_title=owner_job_title,
            owner_bio=owner_bio,
            owner_location=owner_location,
            assets=assets,
            total_assets=len(assets)
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting delegated assets: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get delegated assets: {str(e)}"
        )


@router.get("/users/{owner_address}/transactions")
async def get_delegated_user_transactions(
    owner_address: str,
    limit: int = Query(50, description="Maximum number of transactions to return"),
    wallet_address: str = Depends(get_wallet_address),
    blockchain_service: BlockchainService = Depends(get_blockchain_service),
    transaction_service: TransactionService = Depends(get_transaction_service)
):
    """
    Get transaction history for a user who has delegated to me.
    
    SECURITY: Always verifies delegation on blockchain before allowing access.
    
    Args:
        owner_address: The address of the user who delegated to me
        limit: Maximum number of transactions to return
        
    Returns:
        Transaction history for the delegated user
    """
    try:
        logger.info(f"Checking blockchain delegation for transaction access: {owner_address} -> {wallet_address}")
        
        # SECURITY: Always check blockchain state (source of truth)
        is_delegated = await blockchain_service.check_delegation(
            owner_address=owner_address,
            delegate_address=wallet_address
        )
        
        if not is_delegated:
            logger.warning(f"Transaction access denied: {owner_address} has not delegated to {wallet_address}")
            raise HTTPException(
                status_code=403,
                detail="Access denied: delegation not found on blockchain"
            )
        
        logger.info(f"Delegation verified on blockchain: {owner_address} -> {wallet_address}")
        
        # Get transaction history for the owner
        transactions = await transaction_service.get_wallet_history(
            wallet_address=owner_address,
            include_all_versions=False,
            limit=limit
        )
        
        return {
            "status": "success",
            "owner_address": owner_address,
            "delegate_address": wallet_address,
            "transactions": transactions,
            "count": len(transactions)
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting delegated user transactions: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get delegated user transactions: {str(e)}"
        )


# Simple monitoring endpoint (blockchain is source of truth)

@router.get("/admin/system-status")
async def get_system_status(
    blockchain_service: BlockchainService = Depends(get_blockchain_service),
    _: Dict[str, Any] = Depends(get_wallet_only_user)
):
    """
    Get basic system status. Database inconsistencies don't matter since 
    blockchain is the source of truth for all operations.
    
    Returns:
        System status information
    """
    try:
        # Check blockchain connectivity
        try:
            current_block = blockchain_service.web3.eth.get_block('latest')['number']
            blockchain_status = "connected"
            blockchain_block = current_block
        except Exception as e:
            blockchain_status = f"error: {str(e)}"
            blockchain_block = None
        
        return {
            "blockchain_status": blockchain_status,
            "current_block": blockchain_block,
            "contract_address": blockchain_service.contract_address,
            "approach": "hybrid_with_blockchain_verification",
            "note": "Database serves as UX cache only. All operations verified on-chain."
        }
        
    except Exception as e:
        logger.error(f"Error getting system status: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get system status: {str(e)}"
        )