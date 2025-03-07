from typing import Optional, Dict, Any, Tuple
import logging
from eth_account.messages import encode_defunct
from web3 import Web3
import os
from dotenv import load_dotenv
from app.repositories.auth_repo import AuthRepository
from app.repositories.user_repo import UserRepository
from app.schemas.auth_schema import NonceResponse, AuthenticationResponse

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
            nonce = await self.auth_repository.get_nonce(wallet_address)
            
            return NonceResponse(
                wallet_address=wallet_address,
                nonce=nonce
            )
            
        except Exception as e:
            logger.error(f"Error getting nonce: {str(e)}")
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
            message = encode_defunct(text=f"I am signing my one-time nonce: {nonce}")
            recovered_address = self.web3.eth.account.recover_message(message, signature=signature)
            
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
            stored_nonce = await self.auth_repository.get_nonce(wallet_address)
            
            if not stored_nonce:
                return False, "No nonce found for this wallet address"
                
            # Verify signature
            if not await self.verify_signature(wallet_address, signature, stored_nonce):
                return False, "Invalid signature"
                
            # Update nonce to prevent replay attacks
            await self.auth_repository.update_nonce(wallet_address)
            
            # Update last login timestamp if user exists
            user = await self.user_repository.get_user_by_wallet(wallet_address)
            if user:
                await self.user_repository.update_last_login(wallet_address)
                
            return True, "Authentication successful"
            
        except Exception as e:
            logger.error(f"Error authenticating: {str(e)}")
            return False, f"Authentication error: {str(e)}"
            
    async def create_session(self, wallet_address: str) -> Optional[str]:
        """
        Create a new session for a wallet address.
        
        Args:
            wallet_address: The wallet address to create session for
            
        Returns:
            Session ID if successful, None otherwise
        """
        try:
            return await self.auth_repository.create_session(wallet_address)
            
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
            return await self.auth_repository.get_session(session_id)
            
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
            return await self.auth_repository.delete_session(session_id)
            
        except Exception as e:
            logger.error(f"Error logging out: {str(e)}")
            return False
