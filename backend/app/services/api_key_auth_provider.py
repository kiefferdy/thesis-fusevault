from typing import Optional, Dict
from datetime import datetime, timezone
import logging
import redis.asyncio as redis
from fastapi import Request, HTTPException, status

from app.config import settings

logger = logging.getLogger(__name__)
from app.repositories.api_key_repo import APIKeyRepository
from app.utilities.api_key_utils import (
    validate_api_key_format,
    validate_api_key_signature,
    get_api_key_hash
)


class APIKeyAuthProvider:
    """Handles API key-based authentication"""
    
    def __init__(self, api_key_repo: APIKeyRepository, redis_client: Optional[redis.Redis] = None):
        self.api_key_repo = api_key_repo
        self.redis_client = redis_client
        self.enabled = settings.api_key_auth_enabled
        
    async def authenticate(self, request: Request) -> Optional[Dict[str, str]]:
        """
        Authenticate a request using API key.
        
        Args:
            request: The FastAPI request object
            
        Returns:
            Dict with wallet_address if authenticated, None otherwise
        """
        if not self.enabled:
            return None
        
        try:
            # Check for API key in header first
            api_key = request.headers.get("X-API-Key")
            
            # If not in header, check query parameter (for EventSource compatibility)
            if not api_key:
                api_key = request.query_params.get("key")
            
            if not api_key:
                return None
            
            # Strip whitespace that might cause issues
            api_key = api_key.strip()
            if not api_key:
                return None
                
            # Validate format
            if not validate_api_key_format(api_key):
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Invalid API key format"
                )
                
            # Validate signature
            if not validate_api_key_signature(api_key, settings.api_key_secret_key):
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Invalid API key signature"
                )
                
            # Get key hash
            key_hash = get_api_key_hash(api_key)
            
            # Get API key data first to get wallet address for rate limiting
            api_key_data = await self.api_key_repo.validate_and_get_api_key(key_hash)
            if not api_key_data:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Invalid or expired API key"
                )
            
            # Check rate limit per wallet address (not per API key)
            is_rate_limited = await self._check_rate_limit(api_key_data.wallet_address)
            if is_rate_limited:
                raise HTTPException(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    detail="Rate limit exceeded"
                )
                
            # Return wallet context
            return {
                "wallet_address": api_key_data.wallet_address,
                "auth_method": "api_key",
                "permissions": api_key_data.permissions
            }
            
        except HTTPException:
            # Re-raise HTTP exceptions as-is
            raise
        except Exception as e:
            # Catch any unexpected errors and convert to 401
            logger.error(f"Unexpected error during API key authentication: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Authentication failed"
            )
    
    async def _check_rate_limit(self, wallet_address: str) -> bool:
        """
        Check if the wallet has exceeded rate limit for API key usage.
        Rate limiting is enforced per wallet address to prevent bypass via multiple API keys.
        
        Args:
            wallet_address: The wallet address to check rate limits for
            
        Returns:
            True if rate limited, False otherwise
            
        Raises:
            HTTPException: If Redis is not available (fail closed for security)
        """
        if not self.redis_client:
            logger.error("Redis client not available for API key rate limiting")
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Rate limiting service unavailable"
            )
        
        try:
            # Create rate limit key per wallet address (not per API key)
            rate_limit_key = f"rate_limit:wallet:{wallet_address.lower()}"
            
            # Get current minute timestamp
            current_minute = int(datetime.now(timezone.utc).timestamp() / 60)
            minute_key = f"{rate_limit_key}:{current_minute}"
            
            # Increment counter
            count = await self.redis_client.incr(minute_key)
            
            # Set expiration on first request
            if count == 1:
                await self.redis_client.expire(minute_key, 120)  # Expire after 2 minutes
            
            # Log rate limiting activity
            if count > settings.api_key_rate_limit_per_minute:
                logger.warning(
                    f"Rate limit exceeded for wallet {wallet_address}: "
                    f"{count} requests in current minute (limit: {settings.api_key_rate_limit_per_minute})"
                )
                return True
            else:
                logger.debug(
                    f"Rate limit check for wallet {wallet_address}: "
                    f"{count}/{settings.api_key_rate_limit_per_minute} requests"
                )
                return False
            
        except Exception as e:
            # Fail closed - reject request when rate limiting fails
            logger.error(f"Redis rate limiting failed for wallet {wallet_address}: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Rate limiting service unavailable"
            )
    
    def check_permission(self, required_permission: str, permissions: list) -> bool:
        """
        Check if the API key has the required permission.
        
        Args:
            required_permission: The permission required
            permissions: List of permissions the API key has
            
        Returns:
            True if permission granted, False otherwise
        """
        # Handle edge cases
        if not permissions or not isinstance(permissions, list):
            return False
            
        # Check specific permission
        return required_permission in permissions