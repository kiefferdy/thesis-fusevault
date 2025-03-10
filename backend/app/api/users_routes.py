from fastapi import APIRouter, Depends, Body
import logging

from app.handlers.user_handler import UserHandler
from app.schemas.user_schema import UserCreate, UserResponse, UserUpdateRequest, UserDeleteResponse, UsersResponse
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
    result = await user_handler.register_user(user_data)
    return UserResponse(**result)

@router.get("/{wallet_address}", response_model=UserResponse)
async def get_user(
    wallet_address: str,
    user_handler: UserHandler = Depends(get_user_handler)
) -> UserResponse:
    """
    Get a user by wallet address.
    
    Args:
        wallet_address: The wallet address to look up
        
    Returns:
        UserResponse containing user information
    """
    result = await user_handler.get_user(wallet_address)
    return UserResponse(**result)

@router.put("/{wallet_address}", response_model=UserResponse)
async def update_user(
    wallet_address: str,
    update_data: UserUpdateRequest = Body(...),
    user_handler: UserHandler = Depends(get_user_handler)
) -> UserResponse:
    """
    Update a user's information.
    
    Args:
        wallet_address: The wallet address of the user to update
        update_data: The data to update
        
    Returns:
        UserResponse containing update result
    """
    # Convert Pydantic model to dict, excluding unset fields
    update_dict = update_data.dict(exclude_unset=True)
    result = await user_handler.update_user(wallet_address, update_dict)
    return UserResponse(**result)

@router.delete("/{wallet_address}", response_model=UserDeleteResponse)
async def delete_user(
    wallet_address: str,
    user_handler: UserHandler = Depends(get_user_handler)
) -> UserDeleteResponse:
    """
    Delete a user.
    
    Args:
        wallet_address: The wallet address of the user to delete
        
    Returns:
        UserDeleteResponse containing deletion result
    """
    result = await user_handler.delete_user(wallet_address)
    return UserDeleteResponse(**result)

@router.get("/role/{role}", response_model=UsersResponse)
async def get_users_by_role(
    role: str,
    user_handler: UserHandler = Depends(get_user_handler)
) -> UsersResponse:
    """
    Get all users with a specific role.
    
    Args:
        role: The role to filter by
        
    Returns:
        UsersResponse containing users with the specified role
    """
    result = await user_handler.get_users_by_role(role)
    return UsersResponse(**result)
