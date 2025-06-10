import pytest
from unittest.mock import MagicMock, AsyncMock, patch
from datetime import datetime, timedelta, timezone
from pymongo.errors import DuplicateKeyError
from motor.motor_asyncio import AsyncIOMotorCollection

from app.repositories.api_key_repo import APIKeyRepository
from app.schemas.api_key_schema import APIKeyInDB


class TestAPIKeyRepository:
    """Test suite for API key repository database operations."""

    @pytest.fixture
    def mock_collection(self):
        """Create a mock MongoDB collection."""
        collection = MagicMock(spec=AsyncIOMotorCollection)
        collection.insert_one = AsyncMock()
        collection.find_one = AsyncMock()
        collection.find = MagicMock()
        collection.update_one = AsyncMock()
        collection.delete_many = AsyncMock()
        collection.count_documents = AsyncMock()
        collection.create_indexes = AsyncMock()
        return collection

    @pytest.fixture
    def api_key_repo(self, mock_collection):
        """Create APIKeyRepository with mock collection."""
        return APIKeyRepository(mock_collection)

    @pytest.fixture
    def sample_api_key_data(self, test_wallet_address, test_api_key_hash):
        """Create sample API key data for testing."""
        return APIKeyInDB(
            key_hash=test_api_key_hash,
            wallet_address=test_wallet_address,
            name="Test API Key",
            permissions=["read", "write"],
            expires_at=datetime.now(timezone.utc) + timedelta(days=90),
            metadata={"test": "value"},
            created_at=datetime.now(timezone.utc),
            is_active=True
        )

    @pytest.mark.asyncio
    async def test_create_indexes(self, api_key_repo, mock_collection):
        """Test that indexes are created correctly."""
        await api_key_repo.create_indexes()
        
        # Verify create_indexes was called
        mock_collection.create_indexes.assert_called_once()
        
        # Check the indexes that should be created
        call_args = mock_collection.create_indexes.call_args[0][0]
        index_keys = [list(index.document['key'].keys()) for index in call_args]
        
        # Should have indexes on key_hash (unique), wallet_address, is_active, expires_at
        expected_indexes = [
            ["key_hash"],
            ["wallet_address"],
            ["is_active"],
            ["expires_at"]
        ]
        
        assert len(call_args) == 4
        for expected_index in expected_indexes:
            assert expected_index in index_keys

    @pytest.mark.asyncio
    async def test_create_api_key_success(self, api_key_repo, mock_collection, sample_api_key_data):
        """Test successful API key creation."""
        # Mock successful insertion
        mock_collection.insert_one.return_value = None
        
        result = await api_key_repo.create_api_key(sample_api_key_data)
        
        # Verify insert_one was called with correct data
        mock_collection.insert_one.assert_called_once()
        call_args = mock_collection.insert_one.call_args[0][0]
        
        # Check that all required fields are present
        assert call_args["key_hash"] == sample_api_key_data.key_hash
        assert call_args["wallet_address"] == sample_api_key_data.wallet_address
        assert call_args["name"] == sample_api_key_data.name
        assert call_args["permissions"] == sample_api_key_data.permissions
        assert call_args["is_active"] == sample_api_key_data.is_active
        
        # Should return the same data
        assert result == sample_api_key_data

    @pytest.mark.asyncio
    async def test_get_api_key_by_hash_found(self, api_key_repo, mock_collection, test_api_key_hash, test_api_key_data):
        """Test retrieving API key by hash when it exists."""
        # Mock finding the key
        mock_collection.find_one.return_value = test_api_key_data
        
        result = await api_key_repo.get_api_key_by_hash(test_api_key_hash)
        
        # Verify find_one was called with correct filter
        mock_collection.find_one.assert_called_once_with({"key_hash": test_api_key_hash})
        
        # Should return APIKeyInDB object
        assert isinstance(result, APIKeyInDB)
        assert result.key_hash == test_api_key_data["key_hash"]
        assert result.wallet_address == test_api_key_data["wallet_address"]

    @pytest.mark.asyncio
    async def test_get_api_key_by_hash_not_found(self, api_key_repo, mock_collection, test_api_key_hash):
        """Test retrieving API key by hash when it doesn't exist."""
        # Mock not finding the key
        mock_collection.find_one.return_value = None
        
        result = await api_key_repo.get_api_key_by_hash(test_api_key_hash)
        
        # Should return None
        assert result is None
        mock_collection.find_one.assert_called_once_with({"key_hash": test_api_key_hash})

    @pytest.mark.asyncio
    async def test_get_api_keys_by_wallet(self, api_key_repo, mock_collection, test_wallet_address, test_api_key_data):
        """Test retrieving all API keys for a wallet."""
        # Mock cursor behavior
        mock_cursor = MagicMock()
        mock_cursor.to_list = AsyncMock(return_value=[test_api_key_data, test_api_key_data])
        mock_collection.find.return_value = mock_cursor
        
        result = await api_key_repo.get_api_keys_by_wallet(test_wallet_address)
        
        # Verify find was called with correct filter
        mock_collection.find.assert_called_once_with({"wallet_address": test_wallet_address})
        
        # Should return list of APIKeyInDB objects
        assert len(result) == 2
        assert all(isinstance(key, APIKeyInDB) for key in result)

    @pytest.mark.asyncio
    async def test_get_api_keys_by_wallet_empty(self, api_key_repo, mock_collection, test_wallet_address):
        """Test retrieving API keys for wallet with no keys."""
        # Mock empty cursor
        mock_cursor = MagicMock()
        mock_cursor.to_list = AsyncMock(return_value=[])
        mock_collection.find.return_value = mock_cursor
        
        result = await api_key_repo.get_api_keys_by_wallet(test_wallet_address)
        
        # Should return empty list
        assert result == []

    @pytest.mark.asyncio
    async def test_count_active_keys_for_wallet(self, api_key_repo, mock_collection, test_wallet_address):
        """Test counting active API keys for a wallet."""
        # Mock count result
        mock_collection.count_documents.return_value = 3
        
        result = await api_key_repo.count_active_keys_for_wallet(test_wallet_address)
        
        # Verify count_documents was called with correct filter
        expected_filter = {
            "wallet_address": test_wallet_address,
            "is_active": True
        }
        mock_collection.count_documents.assert_called_once_with(expected_filter)
        
        assert result == 3

    @pytest.mark.asyncio
    async def test_update_last_used_success(self, api_key_repo, mock_collection, test_api_key_hash):
        """Test updating last_used_at timestamp."""
        # Mock successful update
        mock_result = MagicMock()
        mock_result.modified_count = 1
        mock_collection.update_one.return_value = mock_result
        
        with patch('app.repositories.api_key_repo.datetime') as mock_datetime:
            fixed_time = datetime(2025, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
            mock_datetime.now.return_value = fixed_time
            mock_datetime.timezone = timezone
            
            result = await api_key_repo.update_last_used(test_api_key_hash)
        
        # Should return True for successful update
        assert result is True
        
        # Verify update_one was called correctly
        expected_filter = {"key_hash": test_api_key_hash}
        expected_update = {"$set": {"last_used_at": fixed_time}}
        mock_collection.update_one.assert_called_once_with(expected_filter, expected_update)

    @pytest.mark.asyncio
    async def test_update_last_used_not_found(self, api_key_repo, mock_collection, test_api_key_hash):
        """Test updating last_used_at for non-existent key."""
        # Mock no documents modified
        mock_result = MagicMock()
        mock_result.modified_count = 0
        mock_collection.update_one.return_value = mock_result
        
        result = await api_key_repo.update_last_used(test_api_key_hash)
        
        # Should return False for no update
        assert result is False

    @pytest.mark.asyncio
    async def test_update_permissions_success(self, api_key_repo, mock_collection, test_api_key_hash, test_wallet_address):
        """Test updating API key permissions."""
        new_permissions = ["read", "write", "delete"]
        
        # Mock successful update
        mock_result = MagicMock()
        mock_result.modified_count = 1
        mock_collection.update_one.return_value = mock_result
        
        result = await api_key_repo.update_permissions(test_api_key_hash, test_wallet_address, new_permissions)
        
        # Should return True for successful update
        assert result is True
        
        # Verify update_one was called correctly
        expected_filter = {"key_hash": test_api_key_hash, "wallet_address": test_wallet_address}
        expected_update = {"$set": {"permissions": new_permissions}}
        mock_collection.update_one.assert_called_once_with(expected_filter, expected_update)

    @pytest.mark.asyncio
    async def test_update_permissions_unauthorized(self, api_key_repo, mock_collection, test_api_key_hash):
        """Test updating permissions with wrong wallet address."""
        new_permissions = ["read", "write", "delete"]
        wrong_wallet = "0x1234567890123456789012345678901234567890"
        
        # Mock no documents modified (wrong wallet)
        mock_result = MagicMock()
        mock_result.modified_count = 0
        mock_collection.update_one.return_value = mock_result
        
        result = await api_key_repo.update_permissions(test_api_key_hash, wrong_wallet, new_permissions)
        
        # Should return False for unauthorized update
        assert result is False

    @pytest.mark.asyncio
    async def test_deactivate_api_key_success(self, api_key_repo, mock_collection, test_api_key_hash, test_wallet_address):
        """Test deactivating an API key."""
        # Mock successful update
        mock_result = MagicMock()
        mock_result.modified_count = 1
        mock_collection.update_one.return_value = mock_result
        
        result = await api_key_repo.deactivate_api_key(test_api_key_hash, test_wallet_address)
        
        # Should return True for successful deactivation
        assert result is True
        
        # Verify update_one was called correctly
        expected_filter = {"key_hash": test_api_key_hash, "wallet_address": test_wallet_address}
        expected_update = {"$set": {"is_active": False}}
        mock_collection.update_one.assert_called_once_with(expected_filter, expected_update)

    @pytest.mark.asyncio
    async def test_deactivate_api_key_not_found(self, api_key_repo, mock_collection, test_api_key_hash, test_wallet_address):
        """Test deactivating non-existent API key."""
        # Mock no documents modified
        mock_result = MagicMock()
        mock_result.modified_count = 0
        mock_collection.update_one.return_value = mock_result
        
        result = await api_key_repo.deactivate_api_key(test_api_key_hash, test_wallet_address)
        
        # Should return False for not found
        assert result is False

    @pytest.mark.asyncio
    async def test_cleanup_expired_keys(self, api_key_repo, mock_collection):
        """Test cleaning up expired API keys."""
        # Mock deletion result
        mock_result = MagicMock()
        mock_result.deleted_count = 5
        mock_collection.delete_many.return_value = mock_result
        
        with patch('app.repositories.api_key_repo.datetime') as mock_datetime:
            fixed_time = datetime(2025, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
            mock_datetime.now.return_value = fixed_time
            mock_datetime.timezone = timezone
            
            result = await api_key_repo.cleanup_expired_keys()
        
        # Should return number of deleted keys
        assert result == 5
        
        # Verify delete_many was called with correct filter
        expected_filter = {
            "expires_at": {"$lt": fixed_time},
            "is_active": True
        }
        mock_collection.delete_many.assert_called_once_with(expected_filter)

    @pytest.mark.asyncio
    async def test_validate_and_get_api_key_valid_active(self, api_key_repo, mock_collection, test_api_key_hash, test_api_key_data):
        """Test validating and getting a valid, active API key."""
        # Create active, non-expired key data
        active_key_data = test_api_key_data.copy()
        active_key_data["is_active"] = True
        active_key_data["expires_at"] = datetime.now(timezone.utc) + timedelta(days=30)
        active_key_data["key_hash"] = test_api_key_hash  # Use the correct hash
        
        # Mock finding the key
        mock_collection.find_one.return_value = active_key_data
        
        # Mock update for last_used
        mock_result = MagicMock()
        mock_result.modified_count = 1
        mock_collection.update_one.return_value = mock_result
        
        result = await api_key_repo.validate_and_get_api_key(test_api_key_hash)
        
        # Should return the API key
        assert isinstance(result, APIKeyInDB)
        assert result.key_hash == test_api_key_hash
        assert result.is_active is True
        
        # Should update last_used_at
        mock_collection.update_one.assert_called()

    @pytest.mark.asyncio
    async def test_validate_and_get_api_key_not_found(self, api_key_repo, mock_collection, test_api_key_hash):
        """Test validating non-existent API key."""
        # Mock not finding the key
        mock_collection.find_one.return_value = None
        
        result = await api_key_repo.validate_and_get_api_key(test_api_key_hash)
        
        # Should return None
        assert result is None

    @pytest.mark.asyncio
    async def test_validate_and_get_api_key_inactive(self, api_key_repo, mock_collection, test_api_key_hash, test_api_key_data):
        """Test validating inactive API key."""
        # Create inactive key data
        inactive_key_data = test_api_key_data.copy()
        inactive_key_data["is_active"] = False
        
        # Mock finding the inactive key
        mock_collection.find_one.return_value = inactive_key_data
        
        result = await api_key_repo.validate_and_get_api_key(test_api_key_hash)
        
        # Should return None for inactive key
        assert result is None

    @pytest.mark.asyncio
    async def test_validate_and_get_api_key_expired(self, api_key_repo, mock_collection, test_api_key_hash, test_api_key_data):
        """Test validating expired API key."""
        # Create expired key data
        expired_key_data = test_api_key_data.copy()
        expired_key_data["is_active"] = True
        expired_key_data["expires_at"] = datetime.now(timezone.utc) - timedelta(days=1)  # Expired
        
        # Mock finding the expired key
        mock_collection.find_one.return_value = expired_key_data
        
        # Mock deactivation update
        mock_result = MagicMock()
        mock_result.modified_count = 1
        mock_collection.update_one.return_value = mock_result
        
        result = await api_key_repo.validate_and_get_api_key(test_api_key_hash)
        
        # Should return None for expired key
        assert result is None
        
        # Should deactivate the expired key
        expected_filter = {"key_hash": test_api_key_hash}
        expected_update = {"$set": {"is_active": False}}
        mock_collection.update_one.assert_called_with(expected_filter, expected_update)

    @pytest.mark.asyncio
    async def test_validate_and_get_api_key_no_expiration(self, api_key_repo, mock_collection, test_api_key_hash, test_api_key_data):
        """Test validating API key with no expiration date."""
        # Create key data with no expiration
        no_expiry_key_data = test_api_key_data.copy()
        no_expiry_key_data["is_active"] = True
        no_expiry_key_data["expires_at"] = None
        no_expiry_key_data["key_hash"] = test_api_key_hash  # Use the correct hash
        
        # Mock finding the key
        mock_collection.find_one.return_value = no_expiry_key_data
        
        # Mock update for last_used
        mock_result = MagicMock()
        mock_result.modified_count = 1
        mock_collection.update_one.return_value = mock_result
        
        result = await api_key_repo.validate_and_get_api_key(test_api_key_hash)
        
        # Should return the API key (no expiration check)
        assert isinstance(result, APIKeyInDB)
        assert result.key_hash == test_api_key_hash

    @pytest.mark.asyncio
    async def test_database_error_handling(self, api_key_repo, mock_collection, sample_api_key_data):
        """Test handling of database errors."""
        # Mock database error on insertion
        mock_collection.insert_one.side_effect = Exception("Database connection error")
        
        # Should propagate the exception
        with pytest.raises(Exception, match="Database connection error"):
            await api_key_repo.create_api_key(sample_api_key_data)

    @pytest.mark.asyncio
    async def test_duplicate_key_error_handling(self, api_key_repo, mock_collection, sample_api_key_data):
        """Test handling of duplicate key errors."""
        # Mock duplicate key error (unique constraint violation)
        mock_collection.insert_one.side_effect = DuplicateKeyError("Duplicate key error")
        
        # Should propagate the exception
        with pytest.raises(DuplicateKeyError):
            await api_key_repo.create_api_key(sample_api_key_data)

    @pytest.mark.asyncio
    async def test_api_key_data_serialization(self, api_key_repo, mock_collection, sample_api_key_data):
        """Test that APIKeyInDB objects are properly serialized for MongoDB."""
        # Mock successful insertion
        mock_collection.insert_one.return_value = None
        
        await api_key_repo.create_api_key(sample_api_key_data)
        
        # Check that model_dump was called (converts Pydantic model to dict)
        call_args = mock_collection.insert_one.call_args[0][0]
        
        # Should be a dictionary with all expected fields
        assert isinstance(call_args, dict)
        assert "key_hash" in call_args
        assert "wallet_address" in call_args
        assert "name" in call_args
        assert "permissions" in call_args
        assert "created_at" in call_args
        assert "is_active" in call_args

    @pytest.mark.asyncio
    async def test_concurrent_operations(self, api_key_repo, mock_collection, test_api_key_hash, test_wallet_address):
        """Test concurrent repository operations."""
        # Mock multiple concurrent operations
        mock_result = MagicMock()
        mock_result.modified_count = 1
        mock_collection.update_one.return_value = mock_result
        mock_collection.count_documents.return_value = 2
        
        # Simulate concurrent operations
        import asyncio
        tasks = [
            api_key_repo.update_last_used(test_api_key_hash),
            api_key_repo.count_active_keys_for_wallet(test_wallet_address),
            api_key_repo.deactivate_api_key(test_api_key_hash, test_wallet_address)
        ]
        
        results = await asyncio.gather(*tasks)
        
        # All operations should complete successfully
        assert results == [True, 2, True]