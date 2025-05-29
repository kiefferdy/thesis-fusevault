from datetime import datetime, timedelta
from typing import List, Optional
from motor.motor_asyncio import AsyncIOMotorCollection
from pymongo import ASCENDING, IndexModel

from app.schemas.api_key_schema import APIKeyInDB
from app.config import settings


class APIKeyRepository:
    def __init__(self, collection: AsyncIOMotorCollection):
        self.collection = collection
        
    async def create_indexes(self):
        """Create required indexes for the API keys collection"""
        indexes = [
            IndexModel([("key_hash", ASCENDING)], unique=True),
            IndexModel([("wallet_address", ASCENDING)]),
            IndexModel([("is_active", ASCENDING)]),
            IndexModel([("expires_at", ASCENDING)])
        ]
        await self.collection.create_indexes(indexes)
    
    async def create_api_key(self, api_key_data: APIKeyInDB) -> APIKeyInDB:
        """
        Create a new API key in the database.
        
        Args:
            api_key_data: The API key data to store
            
        Returns:
            The created API key data
        """
        # Convert to dict and insert
        api_key_dict = api_key_data.model_dump()
        await self.collection.insert_one(api_key_dict)
        
        return api_key_data
    
    async def get_api_key_by_hash(self, key_hash: str) -> Optional[APIKeyInDB]:
        """
        Retrieve an API key by its hash.
        
        Args:
            key_hash: The hash of the API key
            
        Returns:
            The API key data if found, None otherwise
        """
        api_key_dict = await self.collection.find_one({"key_hash": key_hash})
        
        if api_key_dict:
            return APIKeyInDB(**api_key_dict)
        
        return None
    
    async def get_api_keys_by_wallet(self, wallet_address: str) -> List[APIKeyInDB]:
        """
        Get all API keys for a specific wallet address.
        
        Args:
            wallet_address: The wallet address
            
        Returns:
            List of API keys
        """
        cursor = self.collection.find({"wallet_address": wallet_address})
        api_keys = []
        
        async for api_key_dict in cursor:
            api_keys.append(APIKeyInDB(**api_key_dict))
        
        return api_keys
    
    async def count_active_keys_for_wallet(self, wallet_address: str) -> int:
        """
        Count active API keys for a wallet.
        
        Args:
            wallet_address: The wallet address
            
        Returns:
            Number of active API keys
        """
        return await self.collection.count_documents({
            "wallet_address": wallet_address,
            "is_active": True
        })
    
    async def update_last_used(self, key_hash: str) -> bool:
        """
        Update the last_used_at timestamp for an API key.
        
        Args:
            key_hash: The hash of the API key
            
        Returns:
            True if updated, False otherwise
        """
        result = await self.collection.update_one(
            {"key_hash": key_hash},
            {"$set": {"last_used_at": datetime.utcnow()}}
        )
        
        return result.modified_count > 0
    
    async def update_permissions(self, key_hash: str, wallet_address: str, permissions: List[str]) -> bool:
        """
        Update permissions for an API key.
        
        Args:
            key_hash: The hash of the API key
            wallet_address: The wallet address (for ownership verification)
            permissions: New permissions list
            
        Returns:
            True if updated, False otherwise
        """
        result = await self.collection.update_one(
            {"key_hash": key_hash, "wallet_address": wallet_address},
            {"$set": {"permissions": permissions}}
        )
        
        return result.modified_count > 0
    
    async def deactivate_api_key(self, key_hash: str, wallet_address: str) -> bool:
        """
        Deactivate an API key.
        
        Args:
            key_hash: The hash of the API key
            wallet_address: The wallet address (for ownership verification)
            
        Returns:
            True if deactivated, False otherwise
        """
        result = await self.collection.update_one(
            {"key_hash": key_hash, "wallet_address": wallet_address},
            {"$set": {"is_active": False}}
        )
        
        return result.modified_count > 0
    
    async def cleanup_expired_keys(self) -> int:
        """
        Clean up expired API keys.
        
        Returns:
            Number of keys cleaned up
        """
        result = await self.collection.delete_many({
            "expires_at": {"$lt": datetime.utcnow()},
            "is_active": True
        })
        
        return result.deleted_count
    
    async def validate_and_get_api_key(self, key_hash: str) -> Optional[APIKeyInDB]:
        """
        Validate and retrieve an API key, checking active status and expiration.
        
        Args:
            key_hash: The hash of the API key
            
        Returns:
            The API key data if valid, None otherwise
        """
        api_key = await self.get_api_key_by_hash(key_hash)
        
        if not api_key:
            return None
        
        # Check if active
        if not api_key.is_active:
            return None
        
        # Check expiration
        if api_key.expires_at and api_key.expires_at < datetime.utcnow():
            # Deactivate expired key
            await self.collection.update_one(
                {"key_hash": key_hash},
                {"$set": {"is_active": False}}
            )
            return None
        
        # Update last used timestamp
        await self.update_last_used(key_hash)
        
        return api_key