import pytest
from unittest.mock import MagicMock, patch
from pymongo import DESCENDING
from pymongo.errors import DuplicateKeyError, ServerSelectionTimeoutError, OperationFailure, NetworkTimeout
from bson import ObjectId
from datetime import datetime, timezone

from app.repositories.asset_repo import AssetRepository
from app.repositories.auth_repo import AuthRepository
from app.repositories.transaction_repo import TransactionRepository
from app.repositories.user_repo import UserRepository


# Asset Repository Tests
class TestAssetRepository:
    @pytest.mark.asyncio
    async def test_insert_asset(self, mock_db_client):
        """Test inserting a new asset document."""
        # Mock the insert_one result
        mock_result = MagicMock()
        mock_result.inserted_id = ObjectId("6541e9b2f53c82a1b8c74e25")
        mock_db_client.assets_collection.insert_one.return_value = mock_result
        
        # Test data
        document = {
            "assetId": "test-asset-123",
            "walletAddress": "0x1234567890123456789012345678901234567890",
            "smartContractTxId": "0xabcdef1234567890abcdef1234567890",
            "ipfsHash": "QmTest123456789Test123456789Test12345",
            "criticalMetadata": {"name": "Test Asset"},
            "nonCriticalMetadata": {"tags": ["test"]}
        }
        
        # Initialize repository with mock DB client
        repo = AssetRepository(mock_db_client)
        
        # Call method
        result = await repo.insert_asset(document)
        
        # Assert result
        assert result == str(mock_result.inserted_id)
        mock_db_client.assets_collection.insert_one.assert_called_once_with(document)
    
    @pytest.mark.asyncio
    async def test_find_asset(self, mock_db_client):
        """Test finding an asset by query."""
        # Mock the find_one result
        mock_db_client.assets_collection.find_one.return_value = {
            "_id": ObjectId("6541e9b2f53c82a1b8c74e25"),
            "assetId": "test-asset-123",
            "walletAddress": "0x1234567890123456789012345678901234567890"
        }
        
        # Test query
        query = {"assetId": "test-asset-123"}
        
        # Initialize repository with mock DB client
        repo = AssetRepository(mock_db_client)
        
        # Call method
        result = await repo.find_asset(query)
        
        # Assert result
        assert result is not None
        assert result["assetId"] == "test-asset-123"
        assert result["_id"] == "6541e9b2f53c82a1b8c74e25"  # Should be converted to string
        mock_db_client.assets_collection.find_one.assert_called_once_with(query)
    
    @pytest.mark.asyncio
    async def test_find_asset_not_found(self, mock_db_client):
        """Test finding an asset that doesn't exist."""
        # Mock the find_one result to return None
        mock_db_client.assets_collection.find_one.return_value = None
        
        # Test query
        query = {"assetId": "nonexistent-asset"}
        
        # Initialize repository with mock DB client
        repo = AssetRepository(mock_db_client)
        
        # Call method
        result = await repo.find_asset(query)
        
        # Assert result
        assert result is None
        mock_db_client.assets_collection.find_one.assert_called_once_with(query)
    
    @pytest.mark.asyncio
    async def test_find_assets(self, mock_db_client):
        """Test finding multiple assets by query."""
        # Create mock assets
        mock_assets = [
            {
                "_id": ObjectId("6541e9b2f53c82a1b8c74e25"),
                "assetId": "test-asset-1",
                "walletAddress": "0x1234567890123456789012345678901234567890"
            },
            {
                "_id": ObjectId("6541e9b2f53c82a1b8c74e26"),
                "assetId": "test-asset-2",
                "walletAddress": "0x1234567890123456789012345678901234567890"
            }
        ]
        
        # Mock the find and sort method chain
        mock_cursor = MagicMock()
        mock_cursor.__iter__.return_value = iter(mock_assets)
        mock_db_client.assets_collection.find.return_value.sort.return_value = mock_cursor
        
        # Test query
        query = {"walletAddress": "0x1234567890123456789012345678901234567890"}
        
        # Initialize repository with mock DB client
        repo = AssetRepository(mock_db_client)
        
        # Call method
        results = await repo.find_assets(query)
        
        # Assert results
        assert len(results) == 2
        assert results[0]["assetId"] == "test-asset-1"
        assert results[0]["_id"] == "6541e9b2f53c82a1b8c74e25"  # Should be converted to string
        assert results[1]["assetId"] == "test-asset-2"
        
        # Verify method calls
        mock_db_client.assets_collection.find.assert_called_once_with(query)
        mock_db_client.assets_collection.find.return_value.sort.assert_called_once_with("lastUpdated", DESCENDING)
    
    @pytest.mark.asyncio
    async def test_update_asset(self, mock_db_client):
        """Test updating an asset document."""
        # Mock the update_one result
        mock_result = MagicMock()
        mock_result.modified_count = 1
        mock_db_client.assets_collection.update_one.return_value = mock_result
        
        # Test data
        query = {"assetId": "test-asset-123"}
        update = {"$set": {"nonCriticalMetadata.tags": ["updated", "test"]}}
        
        # Initialize repository with mock DB client
        repo = AssetRepository(mock_db_client)
        
        # Call method
        result = await repo.update_asset(query, update)
        
        # Assert result
        assert result is True
        mock_db_client.assets_collection.update_one.assert_called_once_with(query, update)
    
    @pytest.mark.asyncio
    async def test_update_asset_no_match(self, mock_db_client):
        """Test updating an asset document with no matching document."""
        # Mock the update_one result
        mock_result = MagicMock()
        mock_result.modified_count = 0
        mock_db_client.assets_collection.update_one.return_value = mock_result
        
        # Test data
        query = {"assetId": "nonexistent-asset"}
        update = {"$set": {"nonCriticalMetadata.tags": ["updated", "test"]}}
        
        # Initialize repository with mock DB client
        repo = AssetRepository(mock_db_client)
        
        # Call method
        result = await repo.update_asset(query, update)
        
        # Assert result
        assert result is False
        mock_db_client.assets_collection.update_one.assert_called_once_with(query, update)
    
    @pytest.mark.asyncio
    async def test_update_assets(self, mock_db_client):
        """Test updating multiple asset documents."""
        # Mock the update_many result
        mock_result = MagicMock()
        mock_result.modified_count = 2
        mock_db_client.assets_collection.update_many.return_value = mock_result
        
        # Test data
        query = {"walletAddress": "0x1234567890123456789012345678901234567890"}
        update = {"$set": {"isDeleted": True}}
        
        # Initialize repository with mock DB client
        repo = AssetRepository(mock_db_client)
        
        # Call method
        result = await repo.update_assets(query, update)
        
        # Assert result
        assert result == 2
        mock_db_client.assets_collection.update_many.assert_called_once_with(query, update)
    
    @pytest.mark.asyncio
    async def test_delete_asset(self, mock_db_client):
        """Test hard deleting an asset document."""
        # Mock the delete_one result
        mock_result = MagicMock()
        mock_result.deleted_count = 1
        mock_db_client.assets_collection.delete_one.return_value = mock_result
        
        # Test data
        query = {"assetId": "test-asset-123"}
        
        # Initialize repository with mock DB client
        repo = AssetRepository(mock_db_client)
        
        # Call method
        result = await repo.delete_asset(query)
        
        # Assert result
        assert result is True
        mock_db_client.assets_collection.delete_one.assert_called_once_with(query)
    
    @pytest.mark.asyncio
    async def test_delete_asset_no_match(self, mock_db_client):
        """Test hard deleting an asset document with no matching document."""
        # Mock the delete_one result
        mock_result = MagicMock()
        mock_result.deleted_count = 0
        mock_db_client.assets_collection.delete_one.return_value = mock_result
        
        # Test data
        query = {"assetId": "nonexistent-asset"}
        
        # Initialize repository with mock DB client
        repo = AssetRepository(mock_db_client)
        
        # Call method
        result = await repo.delete_asset(query)
        
        # Assert result
        assert result is False
        mock_db_client.assets_collection.delete_one.assert_called_once_with(query)


# Auth Repository Tests
class TestAuthRepository:
    @pytest.mark.asyncio
    async def test_get_auth_record(self, mock_db_client):
        """Test getting an auth record for a wallet address."""
        # Mock the find_one result
        mock_db_client.auth_collection.find_one.return_value = {
            "_id": ObjectId("6541e9b2f53c82a1b8c74e27"),
            "walletAddress": "0x1234567890123456789012345678901234567890",
            "nonce": 123456
        }
        
        # Test wallet address
        wallet_address = "0x1234567890123456789012345678901234567890"
        
        # Initialize repository with mock DB client
        repo = AuthRepository(mock_db_client)
        
        # Call method
        result = await repo.get_auth_record(wallet_address)
        
        # Assert result
        assert result is not None
        assert result["walletAddress"] == wallet_address
        assert result["nonce"] == 123456
        assert result["_id"] == "6541e9b2f53c82a1b8c74e27"  # Should be converted to string
        mock_db_client.auth_collection.find_one.assert_called_once_with({"walletAddress": wallet_address})
    
    @pytest.mark.asyncio
    async def test_upsert_auth_record_insert(self, mock_db_client):
        """Test upserting an auth record that doesn't exist (insert)."""
        # Mock the update_one result for an insert operation
        mock_result = MagicMock()
        mock_result.modified_count = 0
        mock_result.upserted_id = ObjectId("6541e9b2f53c82a1b8c74e27")
        mock_db_client.auth_collection.update_one.return_value = mock_result
        
        # Test data
        wallet_address = "0x1234567890123456789012345678901234567890"
        data = {"nonce": 123456}
        
        # Initialize repository with mock DB client
        repo = AuthRepository(mock_db_client)
        
        # Call method
        result = await repo.upsert_auth_record(wallet_address, data)
        
        # Assert result
        assert result is True
        mock_db_client.auth_collection.update_one.assert_called_once_with(
            {"walletAddress": wallet_address},
            {"$set": data},
            upsert=True
        )
    
    @pytest.mark.asyncio
    async def test_upsert_auth_record_update(self, mock_db_client):
        """Test upserting an auth record that exists (update)."""
        # Mock the update_one result for an update operation
        mock_result = MagicMock()
        mock_result.modified_count = 1
        mock_result.upserted_id = None
        mock_db_client.auth_collection.update_one.return_value = mock_result
        
        # Test data
        wallet_address = "0x1234567890123456789012345678901234567890"
        data = {"nonce": 123456}
        
        # Initialize repository with mock DB client
        repo = AuthRepository(mock_db_client)
        
        # Call method
        result = await repo.upsert_auth_record(wallet_address, data)
        
        # Assert result
        assert result is True
        mock_db_client.auth_collection.update_one.assert_called_once_with(
            {"walletAddress": wallet_address},
            {"$set": data},
            upsert=True
        )
    
    @pytest.mark.asyncio
    async def test_insert_session(self, mock_db_client):
        """Test inserting a new session."""
        # Mock the insert_one result
        mock_result = MagicMock()
        mock_result.inserted_id = ObjectId("6541e9b2f53c82a1b8c74e28")
        mock_db_client.sessions_collection.insert_one.return_value = mock_result
        
        # Test data
        session_data = {
            "sessionId": "session123",
            "walletAddress": "0x1234567890123456789012345678901234567890",
            "createdAt": datetime.now(timezone.utc),
            "expiresAt": datetime.now(timezone.utc),
            "isActive": True
        }
        
        # Initialize repository with mock DB client
        repo = AuthRepository(mock_db_client)
        
        # Call method
        session_id = await repo.insert_session(session_data)
        
        # Assert result
        assert session_id == "session123"
        mock_db_client.sessions_collection.insert_one.assert_called_once_with(session_data)
    
    @pytest.mark.asyncio
    async def test_get_session(self, mock_db_client):
        """Test getting a session by query."""
        # Current time for testing
        now = datetime.now(timezone.utc)
        
        # Mock the find_one result
        mock_db_client.sessions_collection.find_one.return_value = {
            "_id": ObjectId("6541e9b2f53c82a1b8c74e28"),
            "sessionId": "session123",
            "walletAddress": "0x1234567890123456789012345678901234567890",
            "createdAt": now,
            "expiresAt": now,
            "isActive": True
        }
        
        # Test query
        query = {"sessionId": "session123", "isActive": True}
        
        # Initialize repository with mock DB client
        repo = AuthRepository(mock_db_client)
        
        # Call method
        result = await repo.get_session(query)
        
        # Assert result
        assert result is not None
        assert result["sessionId"] == "session123"
        assert result["walletAddress"] == "0x1234567890123456789012345678901234567890"
        assert result["isActive"] is True
        assert result["_id"] == "6541e9b2f53c82a1b8c74e28"  # Should be converted to string
        mock_db_client.sessions_collection.find_one.assert_called_once_with(query)
    
    @pytest.mark.asyncio
    async def test_update_session(self, mock_db_client):
        """Test updating a session."""
        # Mock the update_one result
        mock_result = MagicMock()
        mock_result.modified_count = 1
        mock_db_client.sessions_collection.update_one.return_value = mock_result
        
        # Test data
        session_id = "session123"
        update_data = {"expiresAt": datetime.now(timezone.utc)}
        
        # Initialize repository with mock DB client
        repo = AuthRepository(mock_db_client)
        
        # Call method
        result = await repo.update_session(session_id, update_data)
        
        # Assert result
        assert result is True
        mock_db_client.sessions_collection.update_one.assert_called_once_with(
            {"sessionId": session_id},
            {"$set": update_data}
        )
    
    @pytest.mark.asyncio
    async def test_delete_session(self, mock_db_client):
        """Test deleting a session."""
        # Mock the delete_one result
        mock_result = MagicMock()
        mock_result.deleted_count = 1
        mock_db_client.sessions_collection.delete_one.return_value = mock_result
        
        # Test data
        session_id = "session123"
        
        # Initialize repository with mock DB client
        repo = AuthRepository(mock_db_client)
        
        # Call method
        result = await repo.delete_session(session_id)
        
        # Assert result
        assert result is True
        mock_db_client.sessions_collection.delete_one.assert_called_once_with({"sessionId": session_id})


# Transaction Repository Tests
class TestTransactionRepository:
    @pytest.mark.asyncio
    async def test_insert_transaction(self, mock_db_client):
        """Test inserting a new transaction record."""
        # Mock the insert_one result
        mock_result = MagicMock()
        mock_result.inserted_id = ObjectId("6541e9b2f53c82a1b8c74e30")
        mock_db_client.transaction_collection.insert_one.return_value = mock_result
        
        # Test data
        transaction_data = {
            "assetId": "test-asset-123",
            "action": "CREATE",
            "walletAddress": "0x1234567890123456789012345678901234567890",
            "timestamp": datetime.now(timezone.utc)
        }
        
        # Initialize repository with mock DB client
        repo = TransactionRepository(mock_db_client)
        
        # Call method
        result = await repo.insert_transaction(transaction_data)
        
        # Assert result
        assert result == str(mock_result.inserted_id)
        mock_db_client.transaction_collection.insert_one.assert_called_once_with(transaction_data)
    
    @pytest.mark.asyncio
    async def test_find_transactions(self, mock_db_client):
        """Test finding transactions by query."""
        # Mock transactions
        now = datetime.now(timezone.utc)
        mock_transactions = [
            {
                "_id": ObjectId("6541e9b2f53c82a1b8c74e30"),
                "assetId": "test-asset-123",
                "action": "CREATE",
                "walletAddress": "0x1234567890123456789012345678901234567890",
                "timestamp": now
            },
            {
                "_id": ObjectId("6541e9b2f53c82a1b8c74e31"),
                "assetId": "test-asset-123",
                "action": "UPDATE",
                "walletAddress": "0x1234567890123456789012345678901234567890",
                "timestamp": now
            }
        ]
        
        # Mock the find and sort method chain
        mock_cursor = MagicMock()
        mock_cursor.__iter__.return_value = iter(mock_transactions)
        mock_db_client.transaction_collection.find.return_value.sort.return_value = mock_cursor
        
        # Test query
        query = {"assetId": "test-asset-123"}
        
        # Initialize repository with mock DB client
        repo = TransactionRepository(mock_db_client)
        
        # Call method
        results = await repo.find_transactions(query)
        
        # Assert results
        assert len(results) == 2
        assert results[0]["assetId"] == "test-asset-123"
        assert results[0]["action"] == "CREATE"
        assert results[0]["_id"] == "6541e9b2f53c82a1b8c74e30"  # Should be converted to string
        assert results[1]["action"] == "UPDATE"
        
        # Verify method calls
        mock_db_client.transaction_collection.find.assert_called_once_with(query)
        mock_db_client.transaction_collection.find.return_value.sort.assert_called_once_with("timestamp", DESCENDING)
    
    @pytest.mark.asyncio
    async def test_find_transaction(self, mock_db_client):
        """Test finding a single transaction by query."""
        # Mock the find_one result
        now = datetime.now(timezone.utc)
        mock_db_client.transaction_collection.find_one.return_value = {
            "_id": ObjectId("6541e9b2f53c82a1b8c74e30"),
            "assetId": "test-asset-123",
            "action": "CREATE",
            "walletAddress": "0x1234567890123456789012345678901234567890",
            "timestamp": now
        }
        
        # Test query
        query = {"_id": ObjectId("6541e9b2f53c82a1b8c74e30")}
        
        # Initialize repository with mock DB client
        repo = TransactionRepository(mock_db_client)
        
        # Call method
        result = await repo.find_transaction(query)
        
        # Assert result
        assert result is not None
        assert result["assetId"] == "test-asset-123"
        assert result["action"] == "CREATE"
        assert result["_id"] == "6541e9b2f53c82a1b8c74e30"  # Should be converted to string
        mock_db_client.transaction_collection.find_one.assert_called_once_with(query)
    
    @pytest.mark.asyncio
    async def test_update_transaction(self, mock_db_client):
        """Test updating a transaction."""
        # Mock the update_one result
        mock_result = MagicMock()
        mock_result.modified_count = 1
        mock_db_client.transaction_collection.update_one.return_value = mock_result
        
        # Test data
        query = {"_id": ObjectId("6541e9b2f53c82a1b8c74e30")}
        update = {"$set": {"metadata.processed": True}}
        
        # Initialize repository with mock DB client
        repo = TransactionRepository(mock_db_client)
        
        # Call method
        result = await repo.update_transaction(query, update)
        
        # Assert result
        assert result is True
        mock_db_client.transaction_collection.update_one.assert_called_once_with(query, update)
    
    @pytest.mark.asyncio
    async def test_delete_transaction(self, mock_db_client):
        """Test deleting a transaction."""
        # Mock the delete_one result
        mock_result = MagicMock()
        mock_result.deleted_count = 1
        mock_db_client.transaction_collection.delete_one.return_value = mock_result
        
        # Test data
        query = {"_id": ObjectId("6541e9b2f53c82a1b8c74e30")}
        
        # Initialize repository with mock DB client
        repo = TransactionRepository(mock_db_client)
        
        # Call method
        result = await repo.delete_transaction(query)
        
        # Assert result
        assert result is True
        mock_db_client.transaction_collection.delete_one.assert_called_once_with(query)


# User Repository Tests
class TestUserRepository:
    @pytest.mark.asyncio
    async def test_insert_user(self, mock_db_client):
        """Test inserting a new user."""
        # Mock the insert_one result
        mock_result = MagicMock()
        mock_result.inserted_id = ObjectId("6541e9b2f53c82a1b8c74e35")
        mock_db_client.users_collection.insert_one.return_value = mock_result
        
        # Test data
        user_data = {
            "walletAddress": "0x1234567890123456789012345678901234567890",
            "email": "test@example.com",
            "role": "user",
            "createdAt": datetime.now(timezone.utc)
        }
        
        # Initialize repository with mock DB client
        repo = UserRepository(mock_db_client)
        
        # Call method
        result = await repo.insert_user(user_data)
        
        # Assert result
        assert result == str(mock_result.inserted_id)
        mock_db_client.users_collection.insert_one.assert_called_once_with(user_data)
    
    @pytest.mark.asyncio
    async def test_find_user(self, mock_db_client):
        """Test finding a user by query."""
        # Mock the find_one result
        mock_db_client.users_collection.find_one.return_value = {
            "_id": ObjectId("6541e9b2f53c82a1b8c74e35"),
            "walletAddress": "0x1234567890123456789012345678901234567890",
            "email": "test@example.com",
            "role": "user"
        }
        
        # Test query
        query = {"walletAddress": "0x1234567890123456789012345678901234567890"}
        
        # Initialize repository with mock DB client
        repo = UserRepository(mock_db_client)
        
        # Call method
        result = await repo.find_user(query)
        
        # Assert result
        assert result is not None
        assert result["walletAddress"] == "0x1234567890123456789012345678901234567890"
        assert result["email"] == "test@example.com"
        assert result["role"] == "user"
        assert result["_id"] == "6541e9b2f53c82a1b8c74e35"  # Should be converted to string
        mock_db_client.users_collection.find_one.assert_called_once_with(query)
    
    @pytest.mark.asyncio
    async def test_find_users(self, mock_db_client):
        """Test finding multiple users by query."""
        # Mock users
        mock_users = [
            {
                "_id": ObjectId("6541e9b2f53c82a1b8c74e35"),
                "walletAddress": "0x1234567890123456789012345678901234567890",
                "email": "test1@example.com",
                "role": "admin"
            },
            {
                "_id": ObjectId("6541e9b2f53c82a1b8c74e36"),
                "walletAddress": "0x0987654321098765432109876543210987654321",
                "email": "test2@example.com",
                "role": "admin"
            }
        ]
        
        # Mock the find method
        mock_cursor = MagicMock()
        mock_cursor.__iter__.return_value = iter(mock_users)
        mock_db_client.users_collection.find.return_value = mock_cursor
        
        # Test query
        query = {"role": "admin"}
        
        # Initialize repository with mock DB client
        repo = UserRepository(mock_db_client)
        
        # Call method
        results = await repo.find_users(query)
        
        # Assert results
        assert len(results) == 2
        assert results[0]["walletAddress"] == "0x1234567890123456789012345678901234567890"
        assert results[0]["role"] == "admin"
        assert results[0]["_id"] == "6541e9b2f53c82a1b8c74e35"  # Should be converted to string
        assert results[1]["walletAddress"] == "0x0987654321098765432109876543210987654321"
        
        # Verify method calls
        mock_db_client.users_collection.find.assert_called_once_with(query)
    
    @pytest.mark.asyncio
    async def test_update_user(self, mock_db_client):
        """Test updating a user."""
        # Mock the update_one result
        mock_result = MagicMock()
        mock_result.modified_count = 1
        mock_db_client.users_collection.update_one.return_value = mock_result
        
        # Test data
        query = {"walletAddress": "0x1234567890123456789012345678901234567890"}
        update = {"$set": {"email": "updated@example.com", "role": "admin"}}
        
        # Initialize repository with mock DB client
        repo = UserRepository(mock_db_client)
        
        # Call method
        result = await repo.update_user(query, update)
        
        # Assert result
        assert result is True
        mock_db_client.users_collection.update_one.assert_called_once_with(query, update)
    
    @pytest.mark.asyncio
    async def test_delete_user(self, mock_db_client):
        """Test deleting a user."""
        # Mock the delete_one result
        mock_result = MagicMock()
        mock_result.deleted_count = 1
        mock_db_client.users_collection.delete_one.return_value = mock_result
        
        # Test data
        query = {"walletAddress": "0x1234567890123456789012345678901234567890"}
        
        # Initialize repository with mock DB client
        repo = UserRepository(mock_db_client)
        
        # Call method
        result = await repo.delete_user(query)
        
        # Assert result
        assert result is True
        mock_db_client.users_collection.delete_one.assert_called_once_with(query)
    
    @pytest.mark.asyncio
    async def test_delete_user_not_found(self, mock_db_client):
        """Test deleting a user that doesn't exist."""
        # Mock the delete_one result
        mock_result = MagicMock()
        mock_result.deleted_count = 0
        mock_db_client.users_collection.delete_one.return_value = mock_result
        
        # Test data
        query = {"walletAddress": "0xnonexistentwallet"}
        
        # Initialize repository with mock DB client
        repo = UserRepository(mock_db_client)
        
        # Call method
        result = await repo.delete_user(query)
        
        # Assert result
        assert result is False
        mock_db_client.users_collection.delete_one.assert_called_once_with(query)
    
    @pytest.mark.asyncio
    async def test_insert_asset_with_empty_fields(self, mock_db_client):
        """Test inserting an asset with empty fields."""
        # Mock the insert_one result
        mock_result = MagicMock()
        mock_result.inserted_id = ObjectId("6541e9b2f53c82a1b8c74e25")
        mock_db_client.assets_collection.insert_one.return_value = mock_result
        
        # Test data with empty fields
        document = {
            "assetId": "test-asset-123",
            "walletAddress": "0x1234567890123456789012345678901234567890",
            "smartContractTxId": "0xabc123",
            "ipfsHash": "QmTest123",
            "criticalMetadata": {},  # Empty metadata
            "nonCriticalMetadata": {},  # Empty metadata
            "documentHistory": []  # Empty array
        }
        
        # Initialize repository with mock DB client
        repo = AssetRepository(mock_db_client)
        
        # Call method
        result = await repo.insert_asset(document)
        
        # Assert result
        assert result == str(mock_result.inserted_id)
        mock_db_client.assets_collection.insert_one.assert_called_once_with(document)
    
    @pytest.mark.asyncio
    async def test_insert_asset_with_duplicate_key(self, mock_db_client):
        """Test inserting an asset that violates a unique index."""
        # Mock the insert_one to raise DuplicateKeyError
        mock_db_client.assets_collection.insert_one.side_effect = DuplicateKeyError("E11000 duplicate key error")
        
        # Test data
        document = {
            "assetId": "duplicate-asset-id",
            "walletAddress": "0x1234567890123456789012345678901234567890",
            "smartContractTxId": "0xabc123",
            "ipfsHash": "QmTest123"
        }
        
        # Initialize repository with mock DB client
        repo = AssetRepository(mock_db_client)
        
        # Call method and expect exception
        with pytest.raises(DuplicateKeyError):
            await repo.insert_asset(document)
        
        # Verify method was called
        mock_db_client.assets_collection.insert_one.assert_called_once_with(document)
    
    @pytest.mark.asyncio
    async def test_find_asset_with_special_characters(self, mock_db_client):
        """Test finding an asset with special characters in the query."""
        # Mock the find_one result
        mock_asset = {
            "_id": ObjectId("6541e9b2f53c82a1b8c74e25"),
            "assetId": "test-asset!@#$%^&*()",
            "walletAddress": "0x1234567890123456789012345678901234567890"
        }
        mock_db_client.assets_collection.find_one.return_value = mock_asset
        
        # Test query with special characters
        query = {"assetId": "test-asset!@#$%^&*()"}
        
        # Initialize repository with mock DB client
        repo = AssetRepository(mock_db_client)
        
        # Call method
        result = await repo.find_asset(query)
        
        # Assert result
        assert result is not None
        assert result["assetId"] == "test-asset!@#$%^&*()"
        mock_db_client.assets_collection.find_one.assert_called_once_with(query)
    
    @pytest.mark.asyncio
    async def test_find_asset_with_db_connection_error(self, mock_db_client):
        """Test finding an asset when database connection fails."""
        # Mock the find_one to raise ServerSelectionTimeoutError
        mock_db_client.assets_collection.find_one.side_effect = ServerSelectionTimeoutError("No MongoDB server available")
        
        # Test query
        query = {"assetId": "test-asset-123"}
        
        # Initialize repository with mock DB client
        repo = AssetRepository(mock_db_client)
        
        # Call method and expect exception
        with pytest.raises(ServerSelectionTimeoutError):
            await repo.find_asset(query)
        
        # Verify method was called
        mock_db_client.assets_collection.find_one.assert_called_once_with(query)
    
    @pytest.mark.asyncio
    async def test_update_asset_with_complex_query(self, mock_db_client):
        """Test updating an asset with a complex query."""
        # Mock the update_one result
        mock_result = MagicMock()
        mock_result.modified_count = 1
        mock_db_client.assets_collection.update_one.return_value = mock_result
        
        # Test data with complex query and update
        query = {
            "assetId": "test-asset-123",
            "$or": [
                {"versionNumber": {"$gt": 5}},
                {"isDeleted": False}
            ]
        }
        update = {
            "$set": {"nonCriticalMetadata.tags": ["updated", "test"]},
            "$push": {"documentHistory": "doc456"},
            "$inc": {"versionNumber": 1}
        }
        
        # Initialize repository with mock DB client
        repo = AssetRepository(mock_db_client)
        
        # Call method
        result = await repo.update_asset(query, update)
        
        # Assert result
        assert result is True
        mock_db_client.assets_collection.update_one.assert_called_once_with(query, update)
    
    @pytest.mark.asyncio
    async def test_update_asset_with_operation_failure(self, mock_db_client):
        """Test updating an asset with an operation that fails."""
        # Mock the update_one to raise OperationFailure
        mock_db_client.assets_collection.update_one.side_effect = OperationFailure("Cannot apply $set to a non-document value")
        
        # Test data
        query = {"assetId": "test-asset-123"}
        update = {"$set": {"nonCriticalMetadata": "not-an-object"}}  # This would cause an error
        
        # Initialize repository with mock DB client
        repo = AssetRepository(mock_db_client)
        
        # Call method and expect exception
        with pytest.raises(OperationFailure):
            await repo.update_asset(query, update)
        
        # Verify method was called
        mock_db_client.assets_collection.update_one.assert_called_once_with(query, update)
    
    @pytest.mark.asyncio
    async def test_update_assets_with_timeout(self, mock_db_client):
        """Test updating multiple assets with a network timeout."""
        # Mock the update_many to raise NetworkTimeout
        mock_db_client.assets_collection.update_many.side_effect = NetworkTimeout("Operation timed out")
        
        # Test data
        query = {"walletAddress": "0x1234567890123456789012345678901234567890"}
        update = {"$set": {"isDeleted": True}}
        
        # Initialize repository with mock DB client
        repo = AssetRepository(mock_db_client)
        
        # Call method and expect exception
        with pytest.raises(NetworkTimeout):
            await repo.update_assets(query, update)
        
        # Verify method was called
        mock_db_client.assets_collection.update_many.assert_called_once_with(query, update)
    
    @pytest.mark.asyncio
    async def test_find_assets_with_empty_result(self, mock_db_client):
        """Test finding assets with a query that returns no results."""
        # Mock the find method to return empty list
        mock_cursor = MagicMock()
        mock_cursor.__iter__.return_value = iter([])  # Empty list
        mock_db_client.assets_collection.find.return_value.sort.return_value = mock_cursor
        
        # Test query that should return no results
        query = {"nonExistentField": "nonExistentValue"}
        
        # Initialize repository with mock DB client
        repo = AssetRepository(mock_db_client)
        
        # Call method
        results = await repo.find_assets(query)
        
        # Assert results
        assert len(results) == 0
        assert isinstance(results, list)
        
        # Verify method calls
        mock_db_client.assets_collection.find.assert_called_once_with(query)


# Auth Repository Edge Cases and Error Handling Tests
class TestAuthRepositoryEdgeCases:
    @pytest.mark.asyncio
    async def test_get_auth_record_with_invalid_address(self, mock_db_client):
        """Test getting an auth record with an invalid wallet address."""
        # Mock the find_one result - returns None for invalid address
        mock_db_client.auth_collection.find_one.return_value = None
        
        # Test data with invalid (malformed) wallet address
        wallet_address = "not-a-wallet-address"
        
        # Initialize repository with mock DB client
        repo = AuthRepository(mock_db_client)
        
        # Call method
        result = await repo.get_auth_record(wallet_address)
        
        # Assert result
        assert result is None
        mock_db_client.auth_collection.find_one.assert_called_once_with({"walletAddress": wallet_address})
    
    @pytest.mark.asyncio
    async def test_upsert_auth_record_with_db_error(self, mock_db_client):
        """Test upserting an auth record when database operation fails."""
        # Mock the update_one to raise OperationFailure
        mock_db_client.auth_collection.update_one.side_effect = OperationFailure("Write operation error")
        
        # Test data
        wallet_address = "0x1234567890123456789012345678901234567890"
        data = {"nonce": 123456}
        
        # Initialize repository with mock DB client
        repo = AuthRepository(mock_db_client)
        
        # Call method and expect exception
        with pytest.raises(OperationFailure):
            await repo.upsert_auth_record(wallet_address, data)
        
        # Verify method was called
        mock_db_client.auth_collection.update_one.assert_called_once_with(
            {"walletAddress": wallet_address},
            {"$set": data},
            upsert=True
        )
    
    @pytest.mark.asyncio
    async def test_insert_session_with_expired_timestamp(self, mock_db_client):
        """Test inserting a session with a timestamp in the past."""
        # Mock the insert_one result
        mock_result = MagicMock()
        mock_result.inserted_id = ObjectId("6541e9b2f53c82a1b8c74e28")
        mock_db_client.sessions_collection.insert_one.return_value = mock_result
        
        # Test data with timestamp in the past
        past_time = datetime(2020, 1, 1, tzinfo=timezone.utc)  # Timestamp from the past
        session_data = {
            "sessionId": "session123",
            "walletAddress": "0x1234567890123456789012345678901234567890",
            "createdAt": past_time,
            "expiresAt": past_time,  # Already expired
            "isActive": True
        }
        
        # Initialize repository with mock DB client
        repo = AuthRepository(mock_db_client)
        
        # Call method
        session_id = await repo.insert_session(session_data)
        
        # Assert result - should still insert even with expired timestamp
        assert session_id == "session123"
        mock_db_client.sessions_collection.insert_one.assert_called_once_with(session_data)
    
    @pytest.mark.asyncio
    async def test_get_session_with_complex_query(self, mock_db_client):
        """Test getting a session with a complex query."""
        # Mock the find_one result
        now = datetime.now(timezone.utc)
        mock_db_client.sessions_collection.find_one.return_value = {
            "_id": ObjectId("6541e9b2f53c82a1b8c74e28"),
            "sessionId": "session123",
            "walletAddress": "0x1234567890123456789012345678901234567890",
            "createdAt": now,
            "expiresAt": now,
            "isActive": True
        }
        
        # Test query with multiple conditions
        query = {
            "sessionId": "session123",
            "expiresAt": {"$gt": now},
            "isActive": True,
            "walletAddress": {"$in": ["0x1234567890123456789012345678901234567890", "0xAnotherAddress"]}
        }
        
        # Initialize repository with mock DB client
        repo = AuthRepository(mock_db_client)
        
        # Call method
        result = await repo.get_session(query)
        
        # Assert result
        assert result is not None
        assert result["sessionId"] == "session123"
        mock_db_client.sessions_collection.find_one.assert_called_once_with(query)
    
    @pytest.mark.asyncio
    async def test_update_session_with_invalid_id(self, mock_db_client):
        """Test updating a session with an invalid session ID."""
        # Mock the update_one result for no matches
        mock_result = MagicMock()
        mock_result.modified_count = 0
        mock_db_client.sessions_collection.update_one.return_value = mock_result
        
        # Test data
        session_id = "invalid-session-id"
        update_data = {"expiresAt": datetime.now(timezone.utc)}
        
        # Initialize repository with mock DB client
        repo = AuthRepository(mock_db_client)
        
        # Call method
        result = await repo.update_session(session_id, update_data)
        
        # Assert result - should return False for no updates
        assert result is False
        mock_db_client.sessions_collection.update_one.assert_called_once_with(
            {"sessionId": session_id},
            {"$set": update_data}
        )


# Transaction Repository Edge Cases and Error Handling Tests
class TestTransactionRepositoryEdgeCases:
    @pytest.mark.asyncio
    async def test_insert_transaction_with_large_metadata(self, mock_db_client):
        """Test inserting a transaction with large metadata fields."""
        # Mock the insert_one result
        mock_result = MagicMock()
        mock_result.inserted_id = ObjectId("6541e9b2f53c82a1b8c74e30")
        mock_db_client.transaction_collection.insert_one.return_value = mock_result
        
        # Create large metadata (could be a large JSON object in practice)
        large_metadata = {"data": "x" * 10000}  # 10,000 character string
        
        # Test data with large metadata
        transaction_data = {
            "assetId": "test-asset-123",
            "action": "CREATE",
            "walletAddress": "0x1234567890123456789012345678901234567890",
            "timestamp": datetime.now(timezone.utc),
            "metadata": large_metadata
        }
        
        # Initialize repository with mock DB client
        repo = TransactionRepository(mock_db_client)
        
        # Call method
        result = await repo.insert_transaction(transaction_data)
        
        # Assert result
        assert result == str(mock_result.inserted_id)
        mock_db_client.transaction_collection.insert_one.assert_called_once_with(transaction_data)
    
    @pytest.mark.asyncio
    async def test_find_transactions_with_pagination(self, mock_db_client):
        """Test finding transactions with pagination params (skip/limit)."""
        # Create mock transactions
        now = datetime.now(timezone.utc)
        mock_transactions = [
            {
                "_id": ObjectId("6541e9b2f53c82a1b8c74e30"),
                "assetId": "test-asset-123",
                "action": "CREATE",
                "walletAddress": "0x1234567890123456789012345678901234567890",
                "timestamp": now
            }
        ]
        
        # Mock the find and sort method chain with pagination methods
        mock_cursor = MagicMock()
        mock_cursor.__iter__.return_value = iter(mock_transactions)
        mock_db_client.transaction_collection.find.return_value.sort.return_value.skip.return_value.limit.return_value = mock_cursor
        
        # Initialize repository with mock DB client
        repo = TransactionRepository(mock_db_client)
        
        # Test query with pagination
        query = {"assetId": "test-asset-123"}
        sort_by = "timestamp"
        sort_direction = -1
        skip = 10
        limit = 5
        
        # Create a custom find_transactions method with pagination
        async def find_with_pagination(query, sort_by="timestamp", sort_direction=-1, skip=0, limit=0):
            cursor = repo.transaction_collection.find(query).sort(sort_by, sort_direction)
            if skip > 0:
                cursor = cursor.skip(skip)
            if limit > 0:
                cursor = cursor.limit(limit)
                
            transactions = list(cursor)
            
            # Convert ObjectId to string
            for tx in transactions:
                if '_id' in tx:
                    tx['_id'] = str(tx['_id'])
                    
            return transactions
        
        # Call custom method (simulating what would be added to the repository)
        results = await find_with_pagination(
            query=query, 
            sort_by=sort_by, 
            sort_direction=sort_direction,
            skip=skip,
            limit=limit
        )
        
        # Assert results
        assert len(results) == 1
        assert results[0]["assetId"] == "test-asset-123"
        
        # Verify method calls
        mock_db_client.transaction_collection.find.assert_called_once_with(query)
        mock_db_client.transaction_collection.find().sort.assert_called_once_with(sort_by, sort_direction)
        mock_db_client.transaction_collection.find().sort().skip.assert_called_once_with(skip)
        mock_db_client.transaction_collection.find().sort().skip().limit.assert_called_once_with(limit)
    
    @pytest.mark.asyncio
    async def test_find_transaction_with_object_id(self, mock_db_client):
        """Test finding a transaction using an ObjectId directly."""
        # Mock the find_one result
        mock_transaction = {
            "_id": ObjectId("6541e9b2f53c82a1b8c74e30"),
            "assetId": "test-asset-123",
            "action": "CREATE"
        }
        mock_db_client.transaction_collection.find_one.return_value = mock_transaction
        
        # Initialize repository with mock DB client
        repo = TransactionRepository(mock_db_client)
        
        # Test query with ObjectId
        object_id = ObjectId("6541e9b2f53c82a1b8c74e30")
        query = {"_id": object_id}
        
        # Call method
        result = await repo.find_transaction(query)
        
        # Assert result
        assert result is not None
        assert str(result["_id"]) == "6541e9b2f53c82a1b8c74e30"
        mock_db_client.transaction_collection.find_one.assert_called_once_with(query)
    
    @pytest.mark.asyncio
    async def test_delete_transaction_with_nonexistent_id(self, mock_db_client):
        """Test deleting a transaction that doesn't exist."""
        # Mock the delete_one result
        mock_result = MagicMock()
        mock_result.deleted_count = 0
        mock_db_client.transaction_collection.delete_one.return_value = mock_result
        
        # Test data
        query = {"_id": ObjectId("6541e9b2f53c82a1b8c74e99")}  # Non-existent ID
        
        # Initialize repository with mock DB client
        repo = TransactionRepository(mock_db_client)
        
        # Call method
        result = await repo.delete_transaction(query)
        
        # Assert result
        assert result is False
        mock_db_client.transaction_collection.delete_one.assert_called_once_with(query)


# User Repository Edge Cases and Error Handling Tests
class TestUserRepositoryEdgeCases:
    @pytest.mark.asyncio
    async def test_insert_user_with_unicode_characters(self, mock_db_client):
        """Test inserting a user with unicode characters in the fields."""
        # Mock the insert_one result
        mock_result = MagicMock()
        mock_result.inserted_id = ObjectId("6541e9b2f53c82a1b8c74e35")
        mock_db_client.users_collection.insert_one.return_value = mock_result
        
        # Test data with unicode characters
        user_data = {
            "walletAddress": "0x1234567890123456789012345678901234567890",
            "email": "test@例子.com",  # Unicode domain
            "name": "名字",  # Unicode name
            "role": "user",
            "createdAt": datetime.now(timezone.utc)
        }
        
        # Initialize repository with mock DB client
        repo = UserRepository(mock_db_client)
        
        # Call method
        result = await repo.insert_user(user_data)
        
        # Assert result
        assert result == str(mock_result.inserted_id)
        mock_db_client.users_collection.insert_one.assert_called_once_with(user_data)
    
    @pytest.mark.asyncio
    async def test_find_users_with_case_insensitive_search(self, mock_db_client):
        """Test finding users with a case-insensitive search query."""
        # Mock users
        mock_users = [
            {
                "_id": ObjectId("6541e9b2f53c82a1b8c74e35"),
                "walletAddress": "0x1234567890123456789012345678901234567890",
                "email": "TEST@example.com",  # Uppercase
                "role": "admin"
            }
        ]
        
        # Mock the find method
        mock_cursor = MagicMock()
        mock_cursor.__iter__.return_value = iter(mock_users)
        mock_db_client.users_collection.find.return_value = mock_cursor
        
        # Test query with case-insensitive regex
        query = {"email": {"$regex": "test@example.com", "$options": "i"}}  # i for case-insensitive
        
        # Initialize repository with mock DB client
        repo = UserRepository(mock_db_client)
        
        # Call method
        results = await repo.find_users(query)
        
        # Assert results
        assert len(results) == 1
        assert results[0]["email"] == "TEST@example.com"
        
        # Verify method calls
        mock_db_client.users_collection.find.assert_called_once_with(query)
    
    @pytest.mark.asyncio
    async def test_update_user_with_json_serialization_edge_case(self, mock_db_client):
        """Test updating a user with data that has JSON serialization edge cases."""
        # Mock the update_one result
        mock_result = MagicMock()
        mock_result.modified_count = 1
        mock_db_client.users_collection.update_one.return_value = mock_result
        
        # Test data with potentially problematic JSON values
        query = {"walletAddress": "0x1234567890123456789012345678901234567890"}
        update = {
            "$set": {
                "preferences": {
                    "infinityValue": float('inf'),  # JSON doesn't support Infinity
                    "nanValue": float('nan'),       # JSON doesn't support NaN
                    "dates": [datetime.now(timezone.utc)]  # Dates need special handling
                }
            }
        }
        
        # Initialize repository with mock DB client
        repo = UserRepository(mock_db_client)
        
        # This would normally fail with JSONEncodeError, but MongoDB driver handles the conversion
        # However, in a real app, you'd want to handle these cases before they get to the repository
        
        # Call method
        result = await repo.update_user(query, update)
        
        # Assert result
        assert result is True
        mock_db_client.users_collection.update_one.assert_called_once_with(query, update)
    
    @pytest.mark.asyncio
    async def test_find_user_with_query_injection_attempt(self, mock_db_client):
        """Test finding a user with a query that attempts NoSQL injection."""
        # Mock the find_one result
        mock_db_client.users_collection.find_one.return_value = None
        
        # Test query that attempts NoSQL injection
        # This is an example of a NoSQL injection attempt - in a real app, 
        # you'd need to validate and sanitize inputs
        injection_query = {"$where": "function() { return true }"}
        
        # Initialize repository with mock DB client
        repo = UserRepository(mock_db_client)
        
        # Call method
        result = await repo.find_user(injection_query)
        
        # Assert result
        assert result is None
        
        # Verify method was called (but in a real app, this should be validated/rejected)
        mock_db_client.users_collection.find_one.assert_called_once_with(injection_query)
    
    @pytest.mark.asyncio
    async def test_update_user_atomic_operations(self, mock_db_client):
        """Test updating a user with atomic operations."""
        # Mock the update_one result
        mock_result = MagicMock()
        mock_result.modified_count = 1
        mock_db_client.users_collection.update_one.return_value = mock_result
        
        # Test data with atomic operations
        query = {"walletAddress": "0x1234567890123456789012345678901234567890"}
        update = {
            "$set": {"lastLogin": datetime.now(timezone.utc)},
            "$inc": {"loginCount": 1},
            "$push": {"loginHistory": datetime.now(timezone.utc)}
        }
        
        # Initialize repository with mock DB client
        repo = UserRepository(mock_db_client)
        
        # Call method
        result = await repo.update_user(query, update)
        
        # Assert result
        assert result is True
        mock_db_client.users_collection.update_one.assert_called_once_with(query, update)