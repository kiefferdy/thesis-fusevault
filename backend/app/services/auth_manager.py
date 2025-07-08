from typing import Optional, Dict, List
from fastapi import Request
import logging

from app.services.wallet_auth_provider import WalletAuthProvider
from app.services.api_key_auth_provider import APIKeyAuthProvider
from app.repositories.auth_repo import AuthRepository
from app.repositories.user_repo import UserRepository
from app.repositories.api_key_repo import APIKeyRepository
from app.database import get_db_client
from app.config import settings

logger = logging.getLogger(__name__)


class AuthManager:
    """
    Central authentication manager that coordinates multiple authentication providers.
    Tries wallet authentication first, then API key authentication if enabled.
    """
    
    def __init__(self):
        self.db_client = get_db_client()
        self._setup_providers()
        
    def _setup_providers(self):
        """Initialize authentication providers"""
        # Setup repositories
        auth_repo = AuthRepository(self.db_client)
        user_repo = UserRepository(self.db_client)
        api_key_repo = APIKeyRepository(self.db_client.get_collection("api_keys"))
        
        # Setup wallet auth provider
        self.wallet_auth_provider = WalletAuthProvider(auth_repo, user_repo)
        
        # Setup API key provider if enabled
        redis_client = None
        if settings.api_key_auth_enabled:
            # Redis is mandatory for API keys (enforced by config validation)
            try:
                import redis.asyncio as redis
                redis_client = redis.from_url(settings.redis_url, decode_responses=True)
                logger.info("Redis client initialized for API key rate limiting")
            except Exception as e:
                logger.error(f"Failed to initialize Redis client for API key rate limiting: {e}")
                # This is a critical error since Redis is mandatory for API keys
                raise RuntimeError(
                    f"Redis initialization failed for API key authentication: {e}. "
                    "API keys require Redis for rate limiting."
                )
                
        self.api_key_provider = APIKeyAuthProvider(api_key_repo, redis_client)
        
    async def authenticate(self, request: Request) -> Optional[Dict[str, any]]:
        """
        Authenticate a request using available authentication methods.
        
        Args:
            request: The FastAPI request object
            
        Returns:
            Authentication context dict with wallet_address if authenticated, None otherwise
        """
        # Try wallet authentication first (session cookie)
        session_id = request.cookies.get("session_id")
        if session_id:
            session_data = await self.wallet_auth_provider.validate_session(session_id)
            if session_data:
                logger.debug(f"Authenticated via wallet session: {session_data.get('walletAddress')}")
                return {
                    "wallet_address": session_data.get("walletAddress"),
                    "auth_method": "wallet",
                    "session_data": session_data,
                    "permissions": ["read", "write", "delete"]  # Wallet auth has full permissions
                }
        
        # Try API key authentication if enabled
        if settings.api_key_auth_enabled:
            try:
                auth_context = await self.api_key_provider.authenticate(request)
                if auth_context:
                    logger.debug(f"Authenticated via API key: {auth_context.get('wallet_address')}")
                    return auth_context
            except Exception as e:
                # Log the error but let it propagate to be handled by middleware
                logger.debug(f"API key authentication failed: {str(e)}")
                # Re-raise to let middleware handle the proper HTTP response
                raise
                
        # No authentication method succeeded
        return None
    
    def check_permission(self, auth_context: Dict[str, any], required_permission: str) -> bool:
        """
        Check if the authenticated user has the required permission.
        
        Args:
            auth_context: The authentication context from authenticate()
            required_permission: The permission required (read, write, delete)
            
        Returns:
            True if permission granted, False otherwise
        """
        permissions = auth_context.get("permissions", [])
            
        # Check specific permission
        return required_permission in permissions