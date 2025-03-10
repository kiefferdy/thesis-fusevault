from typing import Optional, Dict, Any
import logging

logger = logging.getLogger(__name__)

class AuthRepository:
    """
    Repository for authentication operations in MongoDB.
    Handles CRUD operations for the auth and sessions collections.
    """
    
    def __init__(self, db_client):
        """
        Initialize with MongoDB client.
        
        Args:
            db_client: The MongoDB client with initialized collections
        """
        self.auth_collection = db_client.auth_collection
        self.sessions_collection = db_client.sessions_collection
        
    async def get_auth_record(self, wallet_address: str) -> Optional[Dict[str, Any]]:
        """
        Get auth record for a wallet address.
        
        Args:
            wallet_address: The wallet address to get record for
            
        Returns:
            Auth record if found, None otherwise
        """
        try:
            auth_record = self.auth_collection.find_one({"walletAddress": wallet_address})
            
            if auth_record:
                auth_record["_id"] = str(auth_record["_id"])
                
            return auth_record
            
        except Exception as e:
            logger.error(f"Error getting auth record: {str(e)}")
            raise
            
    async def upsert_auth_record(self, wallet_address: str, data: Dict[str, Any]) -> bool:
        """
        Insert or update auth record for a wallet address.
        
        Args:
            wallet_address: The wallet address to upsert record for
            data: The data to upsert
            
        Returns:
            True if successful, False otherwise
        """
        try:
            result = self.auth_collection.update_one(
                {"walletAddress": wallet_address},
                {"$set": data},
                upsert=True
            )
            
            return result.modified_count > 0 or result.upserted_id is not None
            
        except Exception as e:
            logger.error(f"Error upserting auth record: {str(e)}")
            raise
            
    async def insert_session(self, session_data: Dict[str, Any]) -> str:
        """
        Insert a new session.
        
        Args:
            session_data: Data for the session
            
        Returns:
            Session ID if successful
        """
        try:
            result = self.sessions_collection.insert_one(session_data)
            session_id = session_data.get("sessionId", str(result.inserted_id))
            
            return session_id
            
        except Exception as e:
            logger.error(f"Error inserting session: {str(e)}")
            raise
            
    async def get_session(self, query: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Get a session by query.
        
        Args:
            query: Query to find the session
            
        Returns:
            Session document if found, None otherwise
        """
        try:
            session = self.sessions_collection.find_one(query)
            
            if session:
                session["_id"] = str(session["_id"])
                
            return session
            
        except Exception as e:
            logger.error(f"Error getting session: {str(e)}")
            raise
            
    async def update_session(self, session_id: str, update: Dict[str, Any]) -> bool:
        """
        Update a session.
        
        Args:
            session_id: The session ID to update
            update: The update operations to perform
            
        Returns:
            True if update was successful, False otherwise
        """
        try:
            result = self.sessions_collection.update_one(
                {"sessionId": session_id},
                {"$set": update}
            )
            
            return result.modified_count > 0
            
        except Exception as e:
            logger.error(f"Error updating session: {str(e)}")
            raise
            
    async def delete_session(self, session_id: str) -> bool:
        """
        Delete a session.
        
        Args:
            session_id: The session ID to delete
            
        Returns:
            True if deletion was successful, False otherwise
        """
        try:
            result = self.sessions_collection.delete_one({"sessionId": session_id})
            
            return result.deleted_count > 0
            
        except Exception as e:
            logger.error(f"Error deleting session: {str(e)}")
            raise
