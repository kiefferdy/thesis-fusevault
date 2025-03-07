from typing import Optional, Dict, Any
from datetime import datetime, timezone
import logging
import secrets
import random

logger = logging.getLogger(__name__)

class AuthRepository:
    """
    Repository for authentication operations in MongoDB.
    Handles nonce generation, verification, and session management.
    """
    
    def __init__(self, db_client):
        """
        Initialize with MongoDB client.
        
        Args:
            db_client: The MongoDB client with initialized collections
        """
        self.auth_collection = db_client.auth_collection
        self.sessions_collection = db_client.sessions_collection
        
    async def get_nonce(self, wallet_address: str) -> int:
        """
        Retrieve nonce for a wallet address, or create a new one if not found.
        
        Args:
            wallet_address: The wallet address to get/create nonce for
            
        Returns:
            The nonce for the wallet address
        """
        try:
            auth_record = self.auth_collection.find_one({"walletAddress": wallet_address})
            
            if auth_record and "nonce" in auth_record:
                return auth_record["nonce"]
                
            return await self.generate_nonce(wallet_address)
            
        except Exception as e:
            logger.error(f"Error getting nonce: {str(e)}")
            raise
            
    async def generate_nonce(self, wallet_address: str) -> int:
        """
        Generate and store a new nonce for a wallet address.
        
        Args:
            wallet_address: The wallet address to generate nonce for
            
        Returns:
            The generated nonce
        """
        try:
            nonce = random.randint(100000, 999999)  # 6-digit nonce
            
            self.auth_collection.update_one(
                {"walletAddress": wallet_address},
                {"$set": {"nonce": nonce}},
                upsert=True
            )
            
            return nonce
            
        except Exception as e:
            logger.error(f"Error generating nonce: {str(e)}")
            raise
            
    async def update_nonce(self, wallet_address: str) -> int:
        """
        Update the nonce for a wallet address after successful authentication.
        
        Args:
            wallet_address: The wallet address to update nonce for
            
        Returns:
            The new nonce
        """
        try:
            return await self.generate_nonce(wallet_address)
            
        except Exception as e:
            logger.error(f"Error updating nonce: {str(e)}")
            raise
            
    async def create_session(self, wallet_address: str, duration: int = 3600) -> str:
        """
        Create a new session for a wallet address.
        
        Args:
            wallet_address: The wallet address to create session for
            duration: Session duration in seconds (default: 1 hour)
            
        Returns:
            The session ID
        """
        try:
            session_id = secrets.token_hex(32)
            expires_at = datetime.now(timezone.utc)
            
            # Add duration in seconds to current time
            expires_at = expires_at.replace(second=expires_at.second + duration)
            
            session = {
                "sessionId": session_id,
                "walletAddress": wallet_address,
                "createdAt": datetime.now(timezone.utc),
                "expiresAt": expires_at,
                "isActive": True
            }
            
            self.sessions_collection.insert_one(session)
            
            return session_id
            
        except Exception as e:
            logger.error(f"Error creating session: {str(e)}")
            raise
            
    async def get_session(self, session_id: str) -> Optional[Dict[str, Any]]:
        """
        Retrieve a session by ID.
        
        Args:
            session_id: The session ID to retrieve
            
        Returns:
            Session document if found and active, None otherwise
        """
        try:
            current_time = datetime.now(timezone.utc)
            
            session = self.sessions_collection.find_one({
                "sessionId": session_id,
                "expiresAt": {"$gt": current_time},
                "isActive": True
            })
            
            if session:
                session["_id"] = str(session["_id"])
                
            return session
            
        except Exception as e:
            logger.error(f"Error getting session: {str(e)}")
            raise
            
    async def delete_session(self, session_id: str) -> bool:
        """
        Delete a session.
        
        Args:
            session_id: The session ID to delete
            
        Returns:
            True if session was deleted, False otherwise
        """
        try:
            result = self.sessions_collection.update_one(
                {"sessionId": session_id},
                {"$set": {"isActive": False}}
            )
            
            return result.modified_count > 0
            
        except Exception as e:
            logger.error(f"Error deleting session: {str(e)}")
            raise
