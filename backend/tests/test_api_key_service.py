import pytest
from unittest.mock import MagicMock, AsyncMock, patch
from datetime import datetime, timedelta

from app.services.api_key_service import APIKeyService
from app.schemas.api_key_schema import APIKeyCreate, APIKeyInDB, APIKeyResponse, APIKeyCreateResponse


class TestAPIKeyService:
    """Test suite for API key service business logic."""

    @pytest.fixture
    def mock_settings(self):
        """Mock application settings for API keys."""
        settings = MagicMock()
        settings.api_key_auth_enabled = True
        settings.api_key_max_per_wallet = 10
        settings.api_key_default_expiration_days = 90
        settings.api_key_default_permissions = ["read"]
        settings.api_key_secret_key = "test_secret_key_for_api_key_signing_minimum_32_characters"
        return settings

    @pytest.fixture
    def api_key_service(self, mock_api_key_repo):
        """Create APIKeyService with mock repository."""
        return APIKeyService(mock_api_key_repo)

    @pytest.fixture
    def sample_api_key_create(self):
        """Create sample API key creation request."""
        return APIKeyCreate(
            name="Test API Key",
            permissions=["read", "write"],
            expires_at=datetime.utcnow() + timedelta(days=30),
            metadata={"purpose": "testing"}
        )

    @pytest.fixture
    def sample_api_key_in_db(self, test_wallet_address, test_api_key_hash):
        """Create sample API key database record."""
        return APIKeyInDB(
            key_hash=test_api_key_hash,
            wallet_address=test_wallet_address,
            name="Test API Key",
            permissions=["read", "write"],
            created_at=datetime.utcnow(),
            last_used_at=None,
            expires_at=datetime.utcnow() + timedelta(days=90),
            is_active=True,
            metadata={"purpose": "testing"}
        )

    @pytest.mark.asyncio
    async def test_create_api_key_success(self, api_key_service, mock_api_key_repo, mock_settings, 
                                        test_wallet_address, sample_api_key_create):
        """Test successful API key creation."""
        # Setup mocks
        mock_api_key_repo.count_active_keys_for_wallet.return_value = 2
        mock_api_key_repo.create_api_key.return_value = None
        
        with patch('app.services.api_key_service.settings', mock_settings), \
             patch('app.services.api_key_service.generate_api_key') as mock_generate:
            
            # Mock key generation
            test_api_key = "fv.v1.231d7d7f.nonce123.signature456"
            test_key_hash = "hash123"
            mock_generate.return_value = (test_api_key, test_key_hash)
            
            result = await api_key_service.create_api_key(test_wallet_address, sample_api_key_create)
        
        # Verify result
        assert isinstance(result, APIKeyCreateResponse)
        assert result.api_key == test_api_key
        assert result.name == sample_api_key_create.name
        assert result.permissions == sample_api_key_create.permissions
        assert result.is_active is True
        
        # Verify repository calls
        mock_api_key_repo.count_active_keys_for_wallet.assert_called_once_with(test_wallet_address)
        mock_api_key_repo.create_api_key.assert_called_once()

    @pytest.mark.asyncio
    async def test_create_api_key_disabled(self, api_key_service, mock_api_key_repo, mock_settings, 
                                         test_wallet_address, sample_api_key_create):
        """Test API key creation when feature is disabled."""
        # Disable API keys
        mock_settings.api_key_auth_enabled = False
        
        with patch('app.services.api_key_service.settings', mock_settings):
            with pytest.raises(ValueError, match="API key authentication is not enabled"):
                await api_key_service.create_api_key(test_wallet_address, sample_api_key_create)

    @pytest.mark.asyncio
    async def test_create_api_key_max_limit_reached(self, api_key_service, mock_api_key_repo, mock_settings,
                                                  test_wallet_address, sample_api_key_create):
        """Test API key creation when maximum limit is reached."""
        # Mock wallet already has maximum keys
        mock_api_key_repo.count_active_keys_for_wallet.return_value = mock_settings.api_key_max_per_wallet
        
        with patch('app.services.api_key_service.settings', mock_settings):
            with pytest.raises(ValueError, match="Maximum API keys limit reached"):
                await api_key_service.create_api_key(test_wallet_address, sample_api_key_create)

    @pytest.mark.asyncio
    async def test_create_api_key_default_expiration(self, api_key_service, mock_api_key_repo, mock_settings,
                                                   test_wallet_address):
        """Test API key creation with default expiration."""
        # Create request without expiration
        api_key_create = APIKeyCreate(
            name="Test Key",
            permissions=["read"]
        )
        
        mock_api_key_repo.count_active_keys_for_wallet.return_value = 0
        mock_api_key_repo.create_api_key.return_value = None
        
        with patch('app.services.api_key_service.settings', mock_settings), \
             patch('app.services.api_key_service.generate_api_key') as mock_generate, \
             patch('app.services.api_key_service.datetime') as mock_datetime:
            
            # Mock current time
            current_time = datetime(2025, 1, 1, 12, 0, 0)
            mock_datetime.utcnow.return_value = current_time
            
            # Mock key generation
            mock_generate.return_value = ("test_key", "test_hash")
            
            await api_key_service.create_api_key(test_wallet_address, api_key_create)
        
        # Verify create_api_key was called with default expiration
        call_args = mock_api_key_repo.create_api_key.call_args[0][0]
        expected_expiration = current_time + timedelta(days=mock_settings.api_key_default_expiration_days)
        assert call_args.expires_at == expected_expiration

    @pytest.mark.asyncio
    async def test_create_api_key_default_permissions(self, api_key_service, mock_api_key_repo, mock_settings,
                                                    test_wallet_address):
        """Test API key creation with default permissions."""
        # Create request without permissions
        api_key_create = APIKeyCreate(
            name="Test Key",
            expires_at=datetime.utcnow() + timedelta(days=30)
        )
        
        mock_api_key_repo.count_active_keys_for_wallet.return_value = 0
        mock_api_key_repo.create_api_key.return_value = None
        
        with patch('app.services.api_key_service.settings', mock_settings), \
             patch('app.services.api_key_service.generate_api_key') as mock_generate:
            
            mock_generate.return_value = ("test_key", "test_hash")
            
            await api_key_service.create_api_key(test_wallet_address, api_key_create)
        
        # Verify create_api_key was called with default permissions
        call_args = mock_api_key_repo.create_api_key.call_args[0][0]
        assert call_args.permissions == mock_settings.api_key_default_permissions

    @pytest.mark.asyncio
    async def test_list_api_keys(self, api_key_service, mock_api_key_repo, test_wallet_address, sample_api_key_in_db):
        """Test listing API keys for a wallet."""
        # Mock repository response
        mock_api_key_repo.get_api_keys_by_wallet.return_value = [sample_api_key_in_db, sample_api_key_in_db]
        
        result = await api_key_service.list_api_keys(test_wallet_address)
        
        # Verify result
        assert len(result) == 2
        assert all(isinstance(key, APIKeyResponse) for key in result)
        
        # Verify API key data is correctly mapped (without sensitive data)
        for api_key_response in result:
            assert api_key_response.name == sample_api_key_in_db.name
            assert api_key_response.permissions == sample_api_key_in_db.permissions
            assert api_key_response.is_active == sample_api_key_in_db.is_active
            # Sensitive data should not be included
            assert not hasattr(api_key_response, 'key_hash')
            assert not hasattr(api_key_response, 'api_key')
        
        # Verify repository call
        mock_api_key_repo.get_api_keys_by_wallet.assert_called_once_with(test_wallet_address)

    @pytest.mark.asyncio
    async def test_list_api_keys_empty(self, api_key_service, mock_api_key_repo, test_wallet_address):
        """Test listing API keys when wallet has no keys."""
        # Mock empty repository response
        mock_api_key_repo.get_api_keys_by_wallet.return_value = []
        
        result = await api_key_service.list_api_keys(test_wallet_address)
        
        # Should return empty list
        assert result == []

    @pytest.mark.asyncio
    async def test_revoke_api_key_success(self, api_key_service, mock_api_key_repo, test_wallet_address, sample_api_key_in_db):
        """Test successful API key revocation."""
        key_name = "Test API Key"
        
        # Mock repository responses
        mock_api_key_repo.get_api_keys_by_wallet.return_value = [sample_api_key_in_db]
        mock_api_key_repo.deactivate_api_key.return_value = True
        
        result = await api_key_service.revoke_api_key(test_wallet_address, key_name)
        
        # Should return True for successful revocation
        assert result is True
        
        # Verify repository calls
        mock_api_key_repo.get_api_keys_by_wallet.assert_called_once_with(test_wallet_address)
        mock_api_key_repo.deactivate_api_key.assert_called_once_with(
            sample_api_key_in_db.key_hash,
            test_wallet_address
        )

    @pytest.mark.asyncio
    async def test_revoke_api_key_not_found(self, api_key_service, mock_api_key_repo, test_wallet_address):
        """Test revoking non-existent API key."""
        key_name = "Nonexistent Key"
        
        # Mock empty repository response
        mock_api_key_repo.get_api_keys_by_wallet.return_value = []
        
        result = await api_key_service.revoke_api_key(test_wallet_address, key_name)
        
        # Should return False for not found
        assert result is False

    @pytest.mark.asyncio
    async def test_revoke_api_key_already_inactive(self, api_key_service, mock_api_key_repo, test_wallet_address):
        """Test revoking already inactive API key."""
        key_name = "Inactive Key"
        
        # Create inactive API key
        inactive_key = APIKeyInDB(
            key_hash="hash123",
            wallet_address=test_wallet_address,
            name=key_name,
            permissions=["read"],
            created_at=datetime.utcnow(),
            expires_at=datetime.utcnow() + timedelta(days=90),
            is_active=False,  # Already inactive
            metadata={}
        )
        
        mock_api_key_repo.get_api_keys_by_wallet.return_value = [inactive_key]
        
        result = await api_key_service.revoke_api_key(test_wallet_address, key_name)
        
        # Should return False for already inactive key
        assert result is False
        
        # Should not call deactivate_api_key
        mock_api_key_repo.deactivate_api_key.assert_not_called()

    @pytest.mark.asyncio
    async def test_revoke_api_key_deactivation_fails(self, api_key_service, mock_api_key_repo, test_wallet_address, sample_api_key_in_db):
        """Test API key revocation when deactivation fails."""
        key_name = "Test API Key"
        
        # Mock repository responses
        mock_api_key_repo.get_api_keys_by_wallet.return_value = [sample_api_key_in_db]
        mock_api_key_repo.deactivate_api_key.return_value = False  # Deactivation fails
        
        result = await api_key_service.revoke_api_key(test_wallet_address, key_name)
        
        # Should return False when deactivation fails
        assert result is False

    @pytest.mark.asyncio
    async def test_update_permissions_success(self, api_key_service, mock_api_key_repo, test_wallet_address, sample_api_key_in_db):
        """Test successful permission update."""
        key_name = "Test API Key"
        new_permissions = ["read", "write", "delete"]
        
        # Mock repository responses
        mock_api_key_repo.get_api_keys_by_wallet.return_value = [sample_api_key_in_db]
        mock_api_key_repo.update_permissions.return_value = True
        
        result = await api_key_service.update_permissions(test_wallet_address, key_name, new_permissions)
        
        # Should return True for successful update
        assert result is True
        
        # Verify repository calls
        mock_api_key_repo.update_permissions.assert_called_once_with(
            sample_api_key_in_db.key_hash,
            test_wallet_address,
            new_permissions
        )

    @pytest.mark.asyncio
    async def test_update_permissions_invalid_permissions(self, api_key_service, mock_api_key_repo, test_wallet_address):
        """Test updating with invalid permissions."""
        key_name = "Test API Key"
        invalid_permissions = ["read", "invalid_permission"]
        
        with pytest.raises(ValueError, match="Invalid permissions"):
            await api_key_service.update_permissions(test_wallet_address, key_name, invalid_permissions)

    @pytest.mark.asyncio
    async def test_update_permissions_key_not_found(self, api_key_service, mock_api_key_repo, test_wallet_address):
        """Test updating permissions for non-existent key."""
        key_name = "Nonexistent Key"
        new_permissions = ["read", "write"]
        
        # Mock empty repository response
        mock_api_key_repo.get_api_keys_by_wallet.return_value = []
        
        result = await api_key_service.update_permissions(test_wallet_address, key_name, new_permissions)
        
        # Should return False for not found
        assert result is False

    @pytest.mark.asyncio
    async def test_update_permissions_inactive_key(self, api_key_service, mock_api_key_repo, test_wallet_address):
        """Test updating permissions for inactive key."""
        key_name = "Inactive Key"
        new_permissions = ["read", "write"]
        
        # Create inactive API key
        inactive_key = APIKeyInDB(
            key_hash="hash123",
            wallet_address=test_wallet_address,
            name=key_name,
            permissions=["read"],
            created_at=datetime.utcnow(),
            expires_at=datetime.utcnow() + timedelta(days=90),
            is_active=False,  # Inactive
            metadata={}
        )
        
        mock_api_key_repo.get_api_keys_by_wallet.return_value = [inactive_key]
        
        result = await api_key_service.update_permissions(test_wallet_address, key_name, new_permissions)
        
        # Should return False for inactive key
        assert result is False
        
        # Should not call update_permissions
        mock_api_key_repo.update_permissions.assert_not_called()

    @pytest.mark.asyncio
    async def test_update_permissions_valid_permission_combinations(self, api_key_service, mock_api_key_repo, 
                                                                  test_wallet_address, sample_api_key_in_db):
        """Test various valid permission combinations."""
        valid_permission_sets = [
            ["read"],
            ["write"],
            ["delete"],
            ["admin"],
            ["read", "write"],
            ["read", "write", "delete"],
            ["read", "write", "delete", "admin"],
        ]
        
        key_name = "Test API Key"
        mock_api_key_repo.get_api_keys_by_wallet.return_value = [sample_api_key_in_db]
        mock_api_key_repo.update_permissions.return_value = True
        
        for permissions in valid_permission_sets:
            result = await api_key_service.update_permissions(test_wallet_address, key_name, permissions)
            assert result is True

    @pytest.mark.asyncio
    async def test_update_permissions_repository_failure(self, api_key_service, mock_api_key_repo, 
                                                       test_wallet_address, sample_api_key_in_db):
        """Test permission update when repository operation fails."""
        key_name = "Test API Key"
        new_permissions = ["read", "write"]
        
        # Mock repository responses
        mock_api_key_repo.get_api_keys_by_wallet.return_value = [sample_api_key_in_db]
        mock_api_key_repo.update_permissions.return_value = False  # Repository operation fails
        
        result = await api_key_service.update_permissions(test_wallet_address, key_name, new_permissions)
        
        # Should return False when repository operation fails
        assert result is False

    @pytest.mark.asyncio
    async def test_key_name_matching_case_sensitive(self, api_key_service, mock_api_key_repo, test_wallet_address):
        """Test that key name matching is case-sensitive."""
        # Create API keys with different case names
        key1 = APIKeyInDB(
            key_hash="hash1",
            wallet_address=test_wallet_address,
            name="Test Key",
            permissions=["read"],
            created_at=datetime.utcnow(),
            expires_at=datetime.utcnow() + timedelta(days=90),
            is_active=True,
            metadata={}
        )
        
        key2 = APIKeyInDB(
            key_hash="hash2",
            wallet_address=test_wallet_address,
            name="test key",  # Different case
            permissions=["read"],
            created_at=datetime.utcnow(),
            expires_at=datetime.utcnow() + timedelta(days=90),
            is_active=True,
            metadata={}
        )
        
        mock_api_key_repo.get_api_keys_by_wallet.return_value = [key1, key2]
        mock_api_key_repo.deactivate_api_key.return_value = True
        
        # Should only match exact case
        result1 = await api_key_service.revoke_api_key(test_wallet_address, "Test Key")
        assert result1 is True
        
        # Reset mock
        mock_api_key_repo.reset_mock()
        mock_api_key_repo.get_api_keys_by_wallet.return_value = [key1, key2]
        mock_api_key_repo.deactivate_api_key.return_value = True
        
        result2 = await api_key_service.revoke_api_key(test_wallet_address, "TEST KEY")
        assert result2 is False  # Should not match different case

    @pytest.mark.asyncio
    async def test_service_handles_repository_exceptions(self, api_key_service, mock_api_key_repo, 
                                                       test_wallet_address, sample_api_key_create):
        """Test service handles repository exceptions gracefully."""
        # Mock repository to raise exception
        mock_api_key_repo.count_active_keys_for_wallet.side_effect = Exception("Database connection error")
        
        with patch('app.services.api_key_service.settings') as mock_settings:
            mock_settings.api_key_auth_enabled = True
            
            # Should propagate the exception
            with pytest.raises(Exception, match="Database connection error"):
                await api_key_service.create_api_key(test_wallet_address, sample_api_key_create)

    @pytest.mark.asyncio
    async def test_metadata_handling(self, api_key_service, mock_api_key_repo, mock_settings, test_wallet_address):
        """Test proper handling of metadata in API key creation."""
        metadata = {
            "purpose": "testing",
            "created_by": "admin",
            "environment": "test"
        }
        
        api_key_create = APIKeyCreate(
            name="Test Key with Metadata",
            permissions=["read"],
            metadata=metadata
        )
        
        mock_api_key_repo.count_active_keys_for_wallet.return_value = 0
        mock_api_key_repo.create_api_key.return_value = None
        
        with patch('app.services.api_key_service.settings', mock_settings), \
             patch('app.services.api_key_service.generate_api_key') as mock_generate:
            
            mock_generate.return_value = ("test_key", "test_hash")
            
            result = await api_key_service.create_api_key(test_wallet_address, api_key_create)
        
        # Verify metadata is preserved
        assert result.metadata == metadata
        
        # Verify metadata is passed to repository
        call_args = mock_api_key_repo.create_api_key.call_args[0][0]
        assert call_args.metadata == metadata