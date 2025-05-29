from typing import Optional, Dict
from datetime import datetime
import redis.asyncio as redis
from fastapi import Request, HTTPException, status

from app.config import settings
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
            
        # Check for API key in header
        api_key = request.headers.get("X-API-Key")
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
        
        # Check rate limit if Redis is available
        if self.redis_client:
            is_rate_limited = await self._check_rate_limit(key_hash)
            if is_rate_limited:
                raise HTTPException(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    detail="Rate limit exceeded"
                )
        
        # Validate and get API key from database
        api_key_data = await self.api_key_repo.validate_and_get_api_key(key_hash)
        if not api_key_data:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid or expired API key"
            )
            
        # Return wallet context
        return {
            "wallet_address": api_key_data.wallet_address,
            "auth_method": "api_key",
            "permissions": api_key_data.permissions
        }
    
    async def _check_rate_limit(self, key_hash: str) -> bool:
        """
        Check if the API key has exceeded rate limit.
        
        Args:
            key_hash: The hash of the API key
            
        Returns:
            True if rate limited, False otherwise
        """
        try:
            # Create rate limit key
            rate_limit_key = f"rate_limit:api_key:{key_hash}"
            
            # Get current minute timestamp
            current_minute = int(datetime.utcnow().timestamp() / 60)
            minute_key = f"{rate_limit_key}:{current_minute}"
            
            # Increment counter
            count = await self.redis_client.incr(minute_key)
            
            # Set expiration on first request
            if count == 1:
                await self.redis_client.expire(minute_key, 120)  # Expire after 2 minutes
            
            # Check if over limit
            return count > settings.api_key_rate_limit_per_minute
            
        except Exception:
            # If Redis fails, allow the request
            return False
    
    def check_permission(self, required_permission: str, permissions: list) -> bool:
        """
        Check if the API key has the required permission.
        
        Args:
            required_permission: The permission required
            permissions: List of permissions the API key has
            
        Returns:
            True if permission granted, False otherwise
        """
        # Admin permission grants all access
        if "admin" in permissions:
            return True
            
        # Check specific permission
        return required_permission in permissions