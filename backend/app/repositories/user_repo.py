from typing import Optional, Dict, Any, List
import logging
from pymongo import ASCENDING, IndexModel
from pymongo.errors import DuplicateKeyError

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
        
    async def create_indexes(self):
        """Create required indexes for the users collection"""
        indexes = [
            IndexModel([("username", ASCENDING)], unique=True),
            IndexModel([("walletAddress", ASCENDING)], unique=True),
            IndexModel([("email", ASCENDING)], sparse=True),  # Sparse index for optional email
            IndexModel([("role", ASCENDING)])
        ]
        await self.users_collection.create_indexes(indexes)
        
    async def insert_user(self, user_data: Dict[str, Any]) -> str:
        """
        Insert a new user.
        
        Args:
            user_data: User data to insert
            
        Returns:
            String ID of the inserted user
        """
        try:
            result = await self.users_collection.insert_one(user_data)
            user_id = str(result.inserted_id)
            
            logger.info(f"User inserted with ID: {user_id}")
            return user_id
            
        except DuplicateKeyError as e:
            logger.error(f"Duplicate key error inserting user: {str(e)}")
            raise  # Re-raise to be handled by the service layer
        except Exception as e:
            logger.error(f"Error inserting user: {str(e)}")
            raise
            
    async def find_user(self, query: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Find a user by query.
        
        Args:
            query: MongoDB query to filter user
            
        Returns:
            User document if found, None otherwise
        """
        try:
            user = await self.users_collection.find_one(query)
            
            if user:
                user["_id"] = str(user["_id"])
                
            return user
            
        except Exception as e:
            logger.error(f"Error finding user: {str(e)}")
            raise
            
    async def find_users(self, query: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Find users by query.
        
        Args:
            query: MongoDB query to filter users
            
        Returns:
            List of user documents
        """
        try:
            cursor = self.users_collection.find(query)
            users = await cursor.to_list(length=None)
            
            for user in users:
                user["_id"] = str(user["_id"])
                
            return users
            
        except Exception as e:
            logger.error(f"Error finding users: {str(e)}")
            raise
            
    async def update_user(self, query: Dict[str, Any], update: Dict[str, Any]) -> bool:
        """
        Update a user.
        
        Args:
            query: Query to identify the user to update
            update: The update operations to perform
            
        Returns:
            True if update was successful, False otherwise
        """
        try:
            result = await self.users_collection.update_one(query, update)
            
            return result.modified_count > 0
            
        except DuplicateKeyError as e:
            logger.error(f"Duplicate key error updating user: {str(e)}")
            raise  # Re-raise to be handled by the service layer
        except Exception as e:
            logger.error(f"Error updating user: {str(e)}")
            raise
            
    async def delete_user(self, query: Dict[str, Any]) -> bool:
        """
        Delete a user.
        
        Args:
            query: Query to identify the user to delete
            
        Returns:
            True if deletion was successful, False otherwise
        """
        try:
            result = await self.users_collection.delete_one(query)
            
            return result.deleted_count > 0
            
        except Exception as e:
            logger.error(f"Error deleting user: {str(e)}")
            raise
    
    async def find_user_by_username(self, username: str) -> Optional[Dict[str, Any]]:
        """
        Find a user by username.
        
        Args:
            username: The username to search for
            
        Returns:
            User document if found, None otherwise
        """
        return await self.find_user({"username": username.lower()})
    
    async def username_exists(self, username: str) -> bool:
        """
        Check if a username already exists.
        
        Args:
            username: The username to check
            
        Returns:
            True if username exists, False otherwise
        """
        user = await self.find_user_by_username(username)
        return user is not None
    
    async def email_exists(self, email: str) -> bool:
        """
        Check if an email already exists (excluding null/empty values).
        
        Args:
            email: The email to check
            
        Returns:
            True if email exists, False otherwise
        """
        if not email:
            return False
        user = await self.find_user({"email": email})
        return user is not None
    
    async def get_users_without_username(self) -> List[Dict[str, Any]]:
        """
        Get all users that don't have a username field (for migration purposes).
        
        Returns:
            List of user documents without username
        """
        try:
            query = {"$or": [{"username": {"$exists": False}}, {"username": None}, {"username": ""}]}
            return await self.find_users(query)
        except Exception as e:
            logger.error(f"Error finding users without username: {str(e)}")
            raise
