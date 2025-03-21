from fastapi import APIRouter, Depends, Body, HTTPException, Request
from typing import Dict, Any, Optional
import logging

from app.handlers.user_handler import UserHandler
from app.schemas.user_schema import UserCreate, UserResponse, UserUpdateRequest, UserDeleteResponse, UsersResponse
from app.services.user_service import UserService
from app.repositories.user_repo import UserRepository
from app.database import get_db_client
from app.utilities.auth_middleware import get_current_user, get_wallet_address

# Setup router
router = APIRouter(
    prefix="/users",
    tags=["Users"],
    responses={404: {"description": "Not found"}},
)

logger = logging.getLogger(__name__)

def get_user_handler(db_client=Depends(get_db_client)) -> UserHandler:
    """Dependency to get the user handler with all required dependencies."""
    user_repo = UserRepository(db_client)
    user_service = UserService(user_repo)
    return UserHandler(user_service)

# This route can remain public, but we'll add authentication for admins in the future
@router.post("/register", response_model=UserResponse)
async def register_user(
    user_data: UserCreate,
    user_handler: UserHandler = Depends(get_user_handler)
) -> UserResponse:
    """
    Register a new user.
    
    Args:
        user_data: User data for registration
        
    Returns:
        UserResponse containing registration result
    """
    return await user_handler.register_user(user_data)

@router.get("/{wallet_address}", response_model=UserResponse)
async def get_user(
    wallet_address: str,
    request: Request,
    user_handler: UserHandler = Depends(get_user_handler),
    current_user: Optional[Dict[str, Any]] = None,
) -> UserResponse:
    """
    Get a user by wallet address.
    User must be authenticated to use this endpoint unless in demo mode.
    
    Args:
        wallet_address: The wallet address to look up
        request: The request object
        user_handler: The user handler
        current_user: The authenticated user data (optional in demo mode)
        
    Returns:
        UserResponse containing user information
    """
    # Check if in demo mode
    demo_mode = getattr(request.state, "demo_mode", False)
    
    if demo_mode:
        # When in demo mode, skip authorization and return demo data
        logger.info(f"Demo mode: Allowing access to user profile for {wallet_address}")
        return await user_handler.get_user(wallet_address, demo_mode=True)
    
    # When not in demo mode, need to get the current_user if it wasn't injected
    if current_user is None:
        try:
            current_user = await get_current_user(request)
        except HTTPException:
            # If no authenticated user, return 401 Unauthorized
            raise HTTPException(
                status_code=401,
                detail="Authentication required to access user profile"
            )
    
    # Verify that the authenticated user is either looking up themselves or is an admin
    authenticated_wallet = current_user.get("walletAddress")
    authenticated_role = current_user.get("role", "user")
    
    is_own_profile = authenticated_wallet.lower() == wallet_address.lower()
    is_admin = authenticated_role == "admin"
    
    if not (is_own_profile or is_admin):
        logger.warning(f"Unauthorized profile access attempt: {authenticated_wallet} tried to access profile of {wallet_address}")
        raise HTTPException(
            status_code=403,
            detail="You can only view your own user profile"
        )
        
    return await user_handler.get_user(wallet_address, demo_mode=False)

@router.put("/{wallet_address}", response_model=UserResponse)
async def update_user(
    wallet_address: str,
    update_data: UserUpdateRequest = Body(...),
    user_handler: UserHandler = Depends(get_user_handler),
    current_user: Dict[str, Any] = Depends(get_current_user)
) -> UserResponse:
    """
    Update a user's information.
    User must be authenticated to use this endpoint.
    
    Args:
        wallet_address: The wallet address of the user to update
        update_data: The data to update
        user_handler: The user handler
        current_user: The authenticated user data
        
    Returns:
        UserResponse containing update result
    """
    # Verify that the authenticated user is updating their own profile or is an admin
    authenticated_wallet = current_user.get("walletAddress")
    authenticated_role = current_user.get("role", "user")
    
    is_own_profile = authenticated_wallet.lower() == wallet_address.lower()
    is_admin = authenticated_role == "admin"
    
    if not (is_own_profile or is_admin):
        logger.warning(f"Unauthorized profile update attempt: {authenticated_wallet} tried to update profile of {wallet_address}")
        raise HTTPException(
            status_code=403,
            detail="You can only update your own user profile"
        )
    
    # Special validation for role updates - only admins can change roles
    if "role" in update_data.dict(exclude_unset=True) and not is_admin:
        logger.warning(f"Unauthorized role update attempt: {authenticated_wallet} tried to change role")
        raise HTTPException(
            status_code=403,
            detail="Only administrators can change user roles"
        )
    
    # Convert Pydantic model to dict, excluding unset fields
    update_dict = update_data.dict(exclude_unset=True)
    return await user_handler.update_user(wallet_address, update_dict)

@router.delete("/{wallet_address}", response_model=UserDeleteResponse)
async def delete_user(
    wallet_address: str,
    user_handler: UserHandler = Depends(get_user_handler),
    current_user: Dict[str, Any] = Depends(get_current_user)
) -> UserDeleteResponse:
    """
    Delete a user.
    User must be authenticated to use this endpoint.
    
    Args:
        wallet_address: The wallet address of the user to delete
        user_handler: The user handler
        current_user: The authenticated user data
        
    Returns:
        UserDeleteResponse containing deletion result
    """
    # Verify that the authenticated user is deleting their own profile or is an admin
    authenticated_wallet = current_user.get("walletAddress")
    authenticated_role = current_user.get("role", "user")
    
    is_own_profile = authenticated_wallet.lower() == wallet_address.lower()
    is_admin = authenticated_role == "admin"
    
    if not (is_own_profile or is_admin):
        logger.warning(f"Unauthorized profile deletion attempt: {authenticated_wallet} tried to delete profile of {wallet_address}")
        raise HTTPException(
            status_code=403,
            detail="You can only delete your own user profile"
        )
        
    result = await user_handler.delete_user(wallet_address)
    return UserDeleteResponse(**result)

@router.get("/role/{role}", response_model=UsersResponse)
async def get_users_by_role(
    role: str,
    user_handler: UserHandler = Depends(get_user_handler),
    current_user: Dict[str, Any] = Depends(get_current_user)
) -> UsersResponse:
    """
    Get all users with a specific role.
    User must be authenticated with admin privileges to use this endpoint.
    
    Args:
        role: The role to filter by
        user_handler: The user handler
        current_user: The authenticated user data
        
    Returns:
        UsersResponse containing users with the specified role
    """
    # This is an admin-only endpoint
    authenticated_role = current_user.get("role", "user")
    
    if authenticated_role != "admin":
        logger.warning(f"Unauthorized admin operation attempt: User {current_user.get('walletAddress')} tried to list users by role")
        raise HTTPException(
            status_code=403,
            detail="Only administrators can list users by role"
        )
        
    result = await user_handler.get_users_by_role(role)
    return UsersResponse(**result)
