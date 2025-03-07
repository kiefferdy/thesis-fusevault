from typing import Optional, Dict, Any, List
from datetime import datetime, timezone
from bson import ObjectId
import logging

logger = logging.getLogger(__name__)

class UserRepository:
    """
    Repository for user operations in MongoDB.
    Handles CRUD operations for the users collection.
    """
    
    def __init__(self, db_client):
        """
        Initialize with MongoDB client.
        
        Args:
            db_client: The MongoDB client with initialized collections
        """
        self.users_collection = db_client.users_collection
        
    async def create_user(
        self, 
        wallet_address: str, 
        email: str,
        role: str = "user"
    ) -> str:
        """
        Create a new user.
        
        Args:
            wallet_address: The user's wallet address
            email: The user's email address
            role: The user's role (default: "user")
            
        Returns:
            String ID of the created user
        """
        try:
            user = {
                "walletAddress": wallet_address,
                "email": email,
                "role": role,
                "createdAt": datetime.now(timezone.utc),
                "lastLogin": None
            }
            
            result = self.users_collection.insert_one(user)
            user_id = str(result.inserted_id)
            
            logger.info(f"User created with ID: {user_id}")
            return user_id
            
        except Exception as e:
            logger.error(f"Error creating user: {str(e)}")
            raise
            
    async def get_user_by_wallet(self, wallet_address: str) -> Optional[Dict[str, Any]]:
        """
        Retrieve a user by wallet address.
        
        Args:
            wallet_address: The wallet address to look up
            
        Returns:
            User document if found, None otherwise
        """
        try:
            user = self.users_collection.find_one({"walletAddress": wallet_address})
            
            if user:
                user["_id"] = str(user["_id"])
                
            return user
            
        except Exception as e:
            logger.error(f"Error getting user by wallet: {str(e)}")
            raise
            
    async def update_user(
        self, 
        wallet_address: str, 
        update_data: Dict[str, Any]
    ) -> bool:
        """
        Update a user's information.
        
        Args:
            wallet_address: The wallet address of the user to update
            update_data: The data to update
            
        Returns:
            True if user was updated, False otherwise
        """
        try:
            result = self.users_collection.update_one(
                {"walletAddress": wallet_address},
                {"$set": update_data}
            )
            
            return result.modified_count > 0
            
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
            result = self.users_collection.update_one(
                {"walletAddress": wallet_address},
                {"$set": {"lastLogin": datetime.now(timezone.utc)}}
            )
            
            return result.modified_count > 0
            
        except Exception as e:
            logger.error(f"Error updating last login: {str(e)}")
            raise
