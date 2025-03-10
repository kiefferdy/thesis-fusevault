from typing import Optional, Dict, Any, List
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
        
    async def insert_user(self, user_data: Dict[str, Any]) -> str:
        """
        Insert a new user.
        
        Args:
            user_data: User data to insert
            
        Returns:
            String ID of the inserted user
        """
        try:
            result = self.users_collection.insert_one(user_data)
            user_id = str(result.inserted_id)
            
            logger.info(f"User inserted with ID: {user_id}")
            return user_id
            
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
            user = self.users_collection.find_one(query)
            
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
            users = list(cursor)
            
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
            result = self.users_collection.update_one(query, update)
            
            return result.modified_count > 0
            
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
            result = self.users_collection.delete_one(query)
            
            return result.deleted_count > 0
            
        except Exception as e:
            logger.error(f"Error deleting user: {str(e)}")
            raise
