from fastapi import APIRouter, Depends, Body
from typing import Dict, Any
import logging

from app.handlers.user_handler import UserHandler
from app.schemas.user_schema import UserCreate, UserResponse
from app.services.user_service import UserService
from app.repositories.user_repo import UserRepository
from app.database import get_db_client

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

@router.post("/register", response_model=Dict[str, Any])
async def register_user(
    user_data: UserCreate,
    user_handler: UserHandler = Depends(get_user_handler)
) -> Dict[str, Any]:
    """
    Register a new user.
    
    Args:
        user_data: User data for registration
        
    Returns:
        Dict containing registration result
    """
    return await user_handler.register_user(user_data)

@router.get("/{wallet_address}", response_model=Dict[str, Any])
async def get_user(
    wallet_address: str,
    user_handler: UserHandler = Depends(get_user_handler)
) -> Dict[str, Any]:
    """
    Get a user by wallet address.
    
    Args:
        wallet_address: The wallet address to look up
        
    Returns:
        Dict containing user information
    """
    return await user_handler.get_user(wallet_address)

@router.put("/{wallet_address}", response_model=Dict[str, Any])
async def update_user(
    wallet_address: str,
    update_data: Dict[str, Any] = Body(...),
    user_handler: UserHandler = Depends(get_user_handler)
) -> Dict[str, Any]:
    """
    Update a user's information.
    
    Args:
        wallet_address: The wallet address of the user to update
        update_data: The data to update
        
    Returns:
        Dict containing update result
    """
    return await user_handler.update_user(wallet_address, update_data)

@router.delete("/{wallet_address}", response_model=Dict[str, Any])
async def delete_user(
    wallet_address: str,
    user_handler: UserHandler = Depends(get_user_handler)
) -> Dict[str, Any]:
    """
    Delete a user.
    
    Args:
        wallet_address: The wallet address of the user to delete
        
    Returns:
        Dict containing deletion result
    """
    return await user_handler.delete_user(wallet_address)

@router.get("/role/{role}", response_model=Dict[str, Any])
async def get_users_by_role(
    role: str,
    user_handler: UserHandler = Depends(get_user_handler)
) -> Dict[str, Any]:
    """
    Get all users with a specific role.
    
    Args:
        role: The role to filter by
        
    Returns:
        Dict containing users with the specified role
    """
    return await user_handler.get_users_by_role(role)
