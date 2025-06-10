from typing import List, Optional
from datetime import datetime, timedelta, timezone
import logging

from app.repositories.api_key_repo import APIKeyRepository
from app.schemas.api_key_schema import (
    APIKeyCreate,
    APIKeyInDB,
    APIKeyResponse,
    APIKeyCreateResponse
)
from app.utilities.api_key_utils import generate_api_key
from app.config import settings

logger = logging.getLogger(__name__)


class APIKeyService:
    """Service for managing API keys"""
    
    def __init__(self, api_key_repo: APIKeyRepository):
        self.api_key_repo = api_key_repo
        
    async def create_api_key(
        self, 
        wallet_address: str, 
        api_key_data: APIKeyCreate
    ) -> APIKeyCreateResponse:
        """
        Create a new API key for a wallet address.
        
        Args:
            wallet_address: The wallet address creating the key
            api_key_data: The API key creation data
            
        Returns:
            The created API key with the actual key value
            
        Raises:
            ValueError: If wallet has too many active keys
        """
        # Check if API keys are enabled
        if not settings.api_key_auth_enabled:
            raise ValueError("API key authentication is not enabled")
            
        # Check existing key count
        active_keys = await self.api_key_repo.count_active_keys_for_wallet(wallet_address)
        if active_keys >= settings.api_key_max_per_wallet:
            raise ValueError(f"Maximum API keys limit reached ({settings.api_key_max_per_wallet})")
            
        # Generate API key
        api_key, key_hash = generate_api_key(wallet_address, settings.api_key_secret_key)
        
        # Set expiration if not provided
        expires_at = api_key_data.expires_at
        if not expires_at:
            expires_at = datetime.now(timezone.utc) + timedelta(days=settings.api_key_default_expiration_days)
            
        # Create API key record
        api_key_db = APIKeyInDB(
            key_hash=key_hash,
            wallet_address=wallet_address,
            name=api_key_data.name,
            permissions=api_key_data.permissions or settings.api_key_default_permissions,
            expires_at=expires_at,
            metadata=api_key_data.metadata,
            created_at=datetime.now(timezone.utc),
            is_active=True
        )
        
        # Save to database
        await self.api_key_repo.create_api_key(api_key_db)
        
        logger.info(f"API key created for wallet {wallet_address}")
        
        # Return response with the actual key
        return APIKeyCreateResponse(
            api_key=api_key,
            name=api_key_db.name,
            permissions=api_key_db.permissions,
            created_at=api_key_db.created_at,
            expires_at=api_key_db.expires_at,
            is_active=api_key_db.is_active,
            metadata=api_key_db.metadata,
            last_used_at=None
        )
    
    async def list_api_keys(self, wallet_address: str) -> List[APIKeyResponse]:
        """
        List all API keys for a wallet address.
        
        Args:
            wallet_address: The wallet address
            
        Returns:
            List of API keys (without the actual key values)
        """
        api_keys = await self.api_key_repo.get_api_keys_by_wallet(wallet_address)
        
        # Convert to response format (without key hash)
        return [
            APIKeyResponse(
                name=key.name,
                permissions=key.permissions,
                created_at=key.created_at,
                last_used_at=key.last_used_at,
                expires_at=key.expires_at,
                is_active=key.is_active,
                metadata=key.metadata
            )
            for key in api_keys
        ]
    
    async def revoke_api_key(self, wallet_address: str, key_name: str) -> bool:
        """
        Revoke an API key by name.
        
        Args:
            wallet_address: The wallet address
            key_name: The name of the key to revoke
            
        Returns:
            True if revoked, False if not found
        """
        # Find the key by name
        api_keys = await self.api_key_repo.get_api_keys_by_wallet(wallet_address)
        
        for key in api_keys:
            if key.name == key_name and key.is_active:
                # Deactivate the key
                success = await self.api_key_repo.deactivate_api_key(
                    key.key_hash, 
                    wallet_address
                )
                if success:
                    logger.info(f"API key '{key_name}' revoked for wallet {wallet_address}")
                return success
                
        return False
    
    async def update_permissions(
        self, 
        wallet_address: str, 
        key_name: str, 
        permissions: List[str]
    ) -> bool:
        """
        Update permissions for an API key.
        
        Args:
            wallet_address: The wallet address
            key_name: The name of the key to update
            permissions: New permissions list
            
        Returns:
            True if updated, False if not found
        """
        # Validate permissions
        valid_permissions = {"read", "write", "delete"}
        if not all(perm in valid_permissions for perm in permissions):
            raise ValueError("Invalid permissions")
            
        # Find the key by name
        api_keys = await self.api_key_repo.get_api_keys_by_wallet(wallet_address)
        
        for key in api_keys:
            if key.name == key_name and key.is_active:
                # Update permissions
                success = await self.api_key_repo.update_permissions(
                    key.key_hash,
                    wallet_address,
                    permissions
                )
                if success:
                    logger.info(f"Permissions updated for API key '{key_name}'")
                return success
                
        return False