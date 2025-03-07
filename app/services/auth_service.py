from typing import Optional, Dict, Any, Tuple
import logging
import random
import secrets
from datetime import datetime, timezone
from eth_account.messages import encode_defunct
from web3 import Web3
import os
from dotenv import load_dotenv
from app.repositories.auth_repo import AuthRepository
from app.repositories.user_repo import UserRepository
from app.schemas.auth_schema import NonceResponse

logger = logging.getLogger(__name__)

class AuthService:
    """
    Service for authentication-related operations.
    Handles nonce generation, verification, and session management.
    """
    
    def __init__(
        self, 
        auth_repository: AuthRepository,
        user_repository: UserRepository
    ):
        """
        Initialize with repositories.
        
        Args:
            auth_repository: Repository for auth data access
            user_repository: Repository for user data access
        """
        self.auth_repository = auth_repository
        self.user_repository = user_repository
        
        # Initialize Web3
        load_dotenv()
        infura_url = os.getenv("INFURA_URL")
        self.web3 = Web3(Web3.HTTPProvider(infura_url))
        
    async def get_nonce(self, wallet_address: str) -> NonceResponse:
        """
        Get or generate nonce for a wallet address.
        
        Args:
            wallet_address: The wallet address to get nonce for
            
        Returns:
            Nonce response with wallet address and nonce
        """
        try:
            # Try to get existing auth record
            auth_record = await self.auth_repository.get_auth_record(wallet_address)
            
            if auth_record and "nonce" in auth_record:
                nonce = auth_record["nonce"]
            else:
                # Generate new nonce
                nonce = await self.generate_nonce(wallet_address)
            
            return NonceResponse(
                wallet_address=wallet_address,
                nonce=nonce
            )
            
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
            
            await self.auth_repository.upsert_auth_record(
                wallet_address,
                {"nonce": nonce}
            )
            
            return nonce
            
        except Exception as e:
            logger.error(f"Error generating nonce: {str(e)}")
            raise
            
    async def verify_signature(
        self,
        wallet_address: str,
        signature: str,
        nonce: int
    ) -> bool:
        """
        Verify a signature against a nonce.
        
        Args:
            wallet_address: The wallet address that signed
            signature: The signature to verify
            nonce: The nonce that was signed
            
        Returns:
            True if signature is valid, False otherwise
        """
        try:
            # Create message that was signed
            message = encode_defunct(text=f"I am signing my one-time nonce: {nonce}")
            
            # Recover the address that signed the message
            recovered_address = self.web3.eth.account.recover_message(message, signature=signature)
            
            # Compare recovered address with provided address (case-insensitive)
            return recovered_address.lower() == wallet_address.lower()
            
        except Exception as e:
            logger.error(f"Error verifying signature: {str(e)}")
            return False
            
    async def authenticate(
        self,
        wallet_address: str,
        signature: str
    ) -> Tuple[bool, str]:
        """
        Authenticate a user with a signature.
        
        Args:
            wallet_address: The wallet address to authenticate
            signature: The signature to verify
            
        Returns:
            Tuple of (success, message)
        """
        try:
            # Get stored nonce
            auth_record = await self.auth_repository.get_auth_record(wallet_address)
            
            if not auth_record or "nonce" not in auth_record:
                return False, "No nonce found for this wallet address"
                
            stored_nonce = auth_record["nonce"]
                
            # Verify signature
            if not await self.verify_signature(wallet_address, signature, stored_nonce):
                return False, "Invalid signature"
                
            # Update nonce to prevent replay attacks
            await self.generate_nonce(wallet_address)
            
            # Update last login timestamp if user exists
            user = await self.user_repository.find_user({"walletAddress": wallet_address})
            if user:
                await self.user_repository.update_user(
                    {"walletAddress": wallet_address},
                    {"$set": {"lastLogin": datetime.now(timezone.utc)}}
                )
                
            return True, "Authentication successful"
            
        except Exception as e:
            logger.error(f"Error authenticating: {str(e)}")
            return False, f"Authentication error: {str(e)}"
            
    async def create_session(self, wallet_address: str, duration: int = 3600) -> Optional[str]:
        """
        Create a new session for a wallet address.
        
        Args:
            wallet_address: The wallet address to create session for
            duration: Session duration in seconds (default: 1 hour)
            
        Returns:
            Session ID if successful, None otherwise
        """
        try:
            session_id = secrets.token_hex(32)
            expires_at = datetime.now(timezone.utc)
            
            # Add duration in seconds to current time
            expires_at = expires_at.replace(second=expires_at.second + duration)
            
            session_data = {
                "sessionId": session_id,
                "walletAddress": wallet_address,
                "createdAt": datetime.now(timezone.utc),
                "expiresAt": expires_at,
                "isActive": True
            }
            
            await self.auth_repository.insert_session(session_data)
            
            return session_id
            
        except Exception as e:
            logger.error(f"Error creating session: {str(e)}")
            return None
            
    async def validate_session(self, session_id: str) -> Optional[Dict[str, Any]]:
        """
        Validate a session.
        
        Args:
            session_id: The session ID to validate
            
        Returns:
            Session data if valid, None otherwise
        """
        try:
            current_time = datetime.now(timezone.utc)
            
            return await self.auth_repository.get_session({
                "sessionId": session_id,
                "expiresAt": {"$gt": current_time},
                "isActive": True
            })
            
        except Exception as e:
            logger.error(f"Error validating session: {str(e)}")
            return None
            
    async def logout(self, session_id: str) -> bool:
        """
        Log out a user by invalidating their session.
        
        Args:
            session_id: The session ID to invalidate
            
        Returns:
            True if session was invalidated, False otherwise
        """
        try:
            return await self.auth_repository.update_session(
                session_id,
                {"isActive": False}
            )
            
        except Exception as e:
            logger.error(f"Error logging out: {str(e)}")
            return False
            
    async def extend_session(self, session_id: str, duration: int = 3600) -> bool:
        """
        Extend the duration of a session.
        
        Args:
            session_id: The session ID to extend
            duration: Additional duration in seconds (default: 1 hour)
            
        Returns:
            True if session was extended, False otherwise
        """
        try:
            session = await self.auth_repository.get_session({"sessionId": session_id})
            
            if not session:
                return False
                
            current_expiry = session["expiresAt"]
            new_expiry = current_expiry.replace(second=current_expiry.second + duration)
            
            return await self.auth_repository.update_session(
                session_id,
                {"expiresAt": new_expiry}
            )
            
        except Exception as e:
            logger.error(f"Error extending session: {str(e)}")
            return False
