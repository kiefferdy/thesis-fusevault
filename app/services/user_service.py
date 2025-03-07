from typing import Optional, Dict, Any, List
import logging
from app.repositories.user_repo import UserRepository
from app.schemas.user_schema import UserCreate, UserResponse

logger = logging.getLogger(__name__)

class UserService:
    """
    Service for user-related operations.
    Encapsulates business logic for user management.
    """
    
    def __init__(self, user_repository: UserRepository):
        """
        Initialize with user repository.
        
        Args:
            user_repository: Repository for user data access
        """
        self.user_repository = user_repository
        
    async def create_user(self, user_data: UserCreate) -> UserResponse:
        """
        Create a new user.
        
        Args:
            user_data: User data for creation
            
        Returns:
            Created user response
            
        Raises:
            ValueError: If user with wallet address already exists
        """
        try:
            # Check if user already exists
            existing_user = await self.user_repository.get_user_by_wallet(user_data.wallet_address)
            
            if existing_user:
                return UserResponse(
                    id=existing_user["_id"],
                    wallet_address=existing_user["walletAddress"],
                    email=existing_user["email"],
                    role=existing_user["role"]
                )
            
            # Create new user
            user_id = await self.user_repository.create_user(
                wallet_address=user_data.wallet_address,
                email=user_data.email,
                role=user_data.role
            )
            
            return UserResponse(
                id=user_id,
                wallet_address=user_data.wallet_address,
                email=user_data.email,
                role=user_data.role
            )
            
        except Exception as e:
            logger.error(f"Error creating user: {str(e)}")
            raise
            
    async def get_user(self, wallet_address: str) -> Optional[UserResponse]:
        """
        Get a user by wallet address.
        
        Args:
            wallet_address: The wallet address to look up
            
        Returns:
            User response if found, None otherwise
        """
        try:
            user = await self.user_repository.get_user_by_wallet(wallet_address)
            
            if not user:
                return None
                
            return UserResponse(
                id=user["_id"],
                wallet_address=user["walletAddress"],
                email=user["email"],
                role=user["role"]
            )
            
        except Exception as e:
            logger.error(f"Error getting user: {str(e)}")
            raise
            
    async def update_user(
        self, 
        wallet_address: str, 
        update_data: Dict[str, Any]
    ) -> Optional[UserResponse]:
        """
        Update a user's information.
        
        Args:
            wallet_address: The wallet address of the user to update
            update_data: The data to update
            
        Returns:
            Updated user response if successful, None otherwise
        """
        try:
            # Check if user exists
            existing_user = await self.user_repository.get_user_by_wallet(wallet_address)
            
            if not existing_user:
                return None
                
            # Format update data for MongoDB (convert keys to camelCase)
            formatted_data = {}
            for key, value in update_data.items():
                if key == "wallet_address":
                    formatted_data["walletAddress"] = value
                elif key == "email":
                    formatted_data["email"] = value
                elif key == "role":
                    formatted_data["role"] = value
                else:
                    formatted_data[key] = value
            
            # Update user
            updated = await self.user_repository.update_user(
                wallet_address=wallet_address,
                update_data=formatted_data
            )
            
            if not updated:
                return None
                
            # Get updated user
            updated_user = await self.user_repository.get_user_by_wallet(wallet_address)
            
            return UserResponse(
                id=updated_user["_id"],
                wallet_address=updated_user["walletAddress"],
                email=updated_user["email"],
                role=updated_user["role"]
            )
            
        except Exception as e:
            logger.error(f"Error updating user: {str(e)}")
            raise
            
    async def update_last_login(self, wallet_address: str) -> bool:
        """
        Update a user's last login timestamp.
        
        Args:
            wallet_address: The wallet address of the user
            
        Returns:
            True if user was updated, False otherwise
        """
        try:
            return await self.user_repository.update_last_login(wallet_address)
            
        except Exception as e:
            logger.error(f"Error updating last login: {str(e)}")
            raise
