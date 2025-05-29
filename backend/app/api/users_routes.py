from fastapi import APIRouter, Depends, Body, HTTPException, Request
from typing import Dict, Any, Optional
import logging

from app.handlers.user_handler import UserHandler
from app.schemas.user_schema import UserCreate, UserResponse, UserUpdateRequest, UserDeleteResponse, UsersResponse
from app.services.user_service import UserService
from app.repositories.user_repo import UserRepository
from app.repositories.auth_repo import AuthRepository
from app.services.auth_service import AuthService
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
    user_handler: UserHandler = Depends(get_user_handler)
) -> UserResponse:
    """
    Get a user by wallet address.
    
    Args:
        wallet_address: The wallet address to look up
        request: The request object
        user_handler: The user handler
        
    Returns:
        UserResponse containing user information
    """
    # Check if in demo mode or unauthenticated
    demo_mode = getattr(request.state, "demo_mode", False)
    is_authenticated = hasattr(request.state, "user") and request.state.user is not None
    
    # If in demo mode or not authenticated, return demo data
    if demo_mode or not is_authenticated:
        logger.info(f"Demo mode or unauthenticated: Allowing public access to user profile for {wallet_address}")
        return await user_handler.get_user(wallet_address, demo_mode=True)
    
    # If authenticated, get user from request state
    current_user = request.state.user
    
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
    request: Request,
    update_data: UserUpdateRequest = Body(...),
    user_handler: UserHandler = Depends(get_user_handler)
) -> UserResponse:
    """
    Update a user's information.
    User must be authenticated to use this endpoint.
    
    Args:
        wallet_address: The wallet address of the user to update
        request: The request object
        update_data: The data to update
        user_handler: The user handler
        
    Returns:
        UserResponse containing update result
    """
    # Extract session ID from cookies (with reduced logging)
    cookies = request.cookies
    session_id = cookies.get("session_id")
    logger.debug(f"Update user request for {wallet_address}")
    logger.debug(f"Session ID available: {session_id is not None}")
    
    # For debugging, try direct validation of the session
    if session_id:
        # Get database client
        db_client = get_db_client()
        
        # Initialize repositories and service
        auth_repo = AuthRepository(db_client)
        user_repo = UserRepository(db_client)
        auth_service = AuthService(auth_repo, user_repo)
        
        # Validate session directly
        session_data = await auth_service.validate_session(session_id)
        
        if session_data:
            # Use this session data if available
            current_user = session_data
            is_authenticated = True
        else:
            # Fall back to request state
            is_authenticated = hasattr(request.state, "user") and request.state.user is not None
            current_user = getattr(request.state, "user", None) if is_authenticated else None
    else:
        # No session ID in cookies, fall back to request state
        is_authenticated = hasattr(request.state, "user") and request.state.user is not None
        current_user = getattr(request.state, "user", None) if is_authenticated else None
    
    if not is_authenticated or not current_user:
        raise HTTPException(
            status_code=401,
            detail="Authentication required to update user profile"
        )
    
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
    request: Request,
    user_handler: UserHandler = Depends(get_user_handler)
) -> UserDeleteResponse:
    """
    Delete a user.
    User must be authenticated to use this endpoint.
    
    Args:
        wallet_address: The wallet address of the user to delete
        request: The request object
        user_handler: The user handler
        
    Returns:
        UserDeleteResponse containing deletion result
    """
    # Get authentication state from request
    is_authenticated = hasattr(request.state, "user") and request.state.user is not None
    
    if not is_authenticated:
        raise HTTPException(
            status_code=401,
            detail="Authentication required to delete user profile"
        )
    
    # Get current user from request state
    current_user = request.state.user
    
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
    request: Request,
    user_handler: UserHandler = Depends(get_user_handler)
) -> UsersResponse:
    """
    Get all users with a specific role.
    User must be authenticated with admin privileges to use this endpoint.
    
    Args:
        role: The role to filter by
        request: The request object
        user_handler: The user handler
        
    Returns:
        UsersResponse containing users with the specified role
    """
    # Get authentication state from request
    is_authenticated = hasattr(request.state, "user") and request.state.user is not None
    
    if not is_authenticated:
        raise HTTPException(
            status_code=401,
            detail="Authentication required to list users by role"
        )
    
    # Get current user from request state
    current_user = request.state.user
    
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
