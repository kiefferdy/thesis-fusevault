from typing import Dict, Any
from fastapi import HTTPException
import logging
from app.services.user_service import UserService
from app.schemas.user_schema import UserCreate

logger = logging.getLogger(__name__)

class UserHandler:
    """
    Handler for user-related operations.
    Acts as a bridge between API routes and the user service layer.
    """
    
    def __init__(self, user_service: UserService):
        """
        Initialize with user service.
        
        Args:
            user_service: Service for user operations
        """
        self.user_service = user_service
        
    async def register_user(self, user_data: UserCreate) -> Dict[str, Any]:
        """
        Register a new user.
        
        Args:
            user_data: User data for registration
            
        Returns:
            Dict containing registration result
            
        Raises:
            HTTPException: If registration fails
        """
        try:
            user = await self.user_service.create_user(user_data)
            
            return {
                "status": "success",
                "user": {
                    "id": user.id,
                    "wallet_address": user.wallet_address,
                    "email": user.email,
                    "role": user.role
                }
            }
            
        except Exception as e:
            logger.error(f"Error registering user: {str(e)}")
            raise HTTPException(status_code=500, detail=f"Error registering user: {str(e)}")
            
    async def get_user(self, wallet_address: str) -> Dict[str, Any]:
        """
        Get a user by wallet address.
        
        Args:
            wallet_address: The wallet address to look up
            
        Returns:
            Dict containing user information
            
        Raises:
            HTTPException: If user not found or retrieval fails
        """
        try:
            user = await self.user_service.get_user(wallet_address)
            
            if not user:
                raise HTTPException(status_code=404, detail="User not found")
                
            return {
                "status": "success",
                "user": {
                    "id": user.id,
                    "wallet_address": user.wallet_address,
                    "email": user.email,
                    "role": user.role
                }
            }
            
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error retrieving user: {str(e)}")
            raise HTTPException(status_code=500, detail=f"Error retrieving user: {str(e)}")
            
    async def update_user(
        self, 
        wallet_address: str, 
        update_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Update a user's information.
        
        Args:
            wallet_address: The wallet address of the user to update
            update_data: The data to update
            
        Returns:
            Dict containing update result
            
        Raises:
            HTTPException: If user not found or update fails
        """
        try:
            updated_user = await self.user_service.update_user(
                wallet_address=wallet_address,
                update_data=update_data
            )
            
            if not updated_user:
                raise HTTPException(status_code=404, detail="User not found")
                
            return {
                "status": "success",
                "user": {
                    "id": updated_user.id,
                    "wallet_address": updated_user.wallet_address,
                    "email": updated_user.email,
                    "role": updated_user.role
                }
            }
            
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error updating user: {str(e)}")
            raise HTTPException(status_code=500, detail=f"Error updating user: {str(e)}")
            
    async def delete_user(self, wallet_address: str) -> Dict[str, Any]:
        """
        Delete a user.
        
        Args:
            wallet_address: The wallet address of the user to delete
            
        Returns:
            Dict containing deletion result
            
        Raises:
            HTTPException: If user not found or deletion fails
        """
        try:
            success = await self.user_service.delete_user(wallet_address)
            
            if not success:
                raise HTTPException(status_code=404, detail="User not found")
                
            return {
                "status": "success",
                "message": "User deleted successfully",
                "wallet_address": wallet_address
            }
            
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error deleting user: {str(e)}")
            raise HTTPException(status_code=500, detail=f"Error deleting user: {str(e)}")
            
    async def get_users_by_role(self, role: str) -> Dict[str, Any]:
        """
        Get all users with a specific role.
        
        Args:
            role: The role to filter by
            
        Returns:
            Dict containing users with the specified role
            
        Raises:
            HTTPException: If retrieval fails
        """
        try:
            users = await self.user_service.get_users_by_role(role)
            
            return {
                "status": "success",
                "role": role,
                "users": [
                    {
                        "id": user.id,
                        "wallet_address": user.wallet_address,
                        "email": user.email,
                        "role": user.role
                    }
                    for user in users
                ],
                "count": len(users)
            }
            
        except Exception as e:
            logger.error(f"Error retrieving users by role: {str(e)}")
            raise HTTPException(status_code=500, detail=f"Error retrieving users by role: {str(e)}")
