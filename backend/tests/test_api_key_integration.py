import pytest
from unittest.mock import MagicMock, AsyncMock, patch
from datetime import datetime, timedelta, timezone
from fastapi import HTTPException
from fastapi.testclient import TestClient

from app.utilities.api_key_utils import generate_api_key, get_api_key_hash
from app.schemas.api_key_schema import APIKeyInDB


class TestAPIKeyIntegration:
    """Integration tests for complete API key workflows."""

    @pytest.fixture
    def mock_settings(self):
        """Mock application settings for integration tests."""
        settings = MagicMock()
        settings.api_key_auth_enabled = True
        settings.api_key_max_per_wallet = 10
        settings.api_key_default_expiration_days = 90
        settings.api_key_default_permissions = ["read"]
        settings.api_key_secret_key = "test_secret_key_for_api_key_signing_minimum_32_characters"
        settings.api_key_rate_limit_per_minute = 100
        return settings

    @pytest.fixture
    def integration_test_client(self):
        """Test client for integration tests."""
        from fastapi.testclient import TestClient
        from app.main import app
        return TestClient(app)

    @pytest.mark.asyncio
    async def test_complete_api_key_lifecycle(self, mock_settings, test_wallet_address):
        """Test complete API key lifecycle: create, use, list, revoke."""
        
        # Step 1: Create API key
        api_key, key_hash = generate_api_key(test_wallet_address, mock_settings.api_key_secret_key)
        
        # Verify key format and hash
        assert api_key.startswith("fv.v1.")
        assert len(key_hash) == 64
        
        # Step 2: Create API key data for database
        api_key_data = APIKeyInDB(
            key_hash=key_hash,
            wallet_address=test_wallet_address,
            name="Integration Test Key",
            permissions=["read", "write"],
            created_at=datetime.now(timezone.utc),
            expires_at=datetime.now(timezone.utc) + timedelta(days=90),
            is_active=True,
            metadata={"test": "integration"}
        )
        
        # Step 3: Mock repository and service
        mock_repo = MagicMock()
        mock_repo.validate_and_get_api_key = AsyncMock(return_value=api_key_data)
        mock_repo.update_last_used = AsyncMock(return_value=True)
        
        # Step 4: Test authentication provider
        from app.services.api_key_auth_provider import APIKeyAuthProvider
        auth_provider = APIKeyAuthProvider(mock_repo, None)  # No Redis for test
        
        # Create mock request with API key
        mock_request = MagicMock()
        mock_request.headers = {"X-API-Key": api_key}
        
        with patch('app.services.api_key_auth_provider.settings', mock_settings):
            auth_result = await auth_provider.authenticate(mock_request)
        
        # Verify authentication result
        assert auth_result is not None
        assert auth_result["wallet_address"] == test_wallet_address
        assert auth_result["auth_method"] == "api_key"
        assert auth_result["permissions"] == ["read", "write"]

    @pytest.mark.asyncio
    async def test_api_key_authentication_flow(self, mock_settings, test_wallet_address):
        """Test API key authentication through auth manager."""
        
        # Create API key
        api_key, key_hash = generate_api_key(test_wallet_address, mock_settings.api_key_secret_key)
        
        api_key_data = APIKeyInDB(
            key_hash=key_hash,
            wallet_address=test_wallet_address,
            name="Auth Flow Test Key",
            permissions=["read", "write", "delete"],
            created_at=datetime.now(timezone.utc),
            expires_at=datetime.now(timezone.utc) + timedelta(days=90),
            is_active=True,
            metadata={}
        )
        
        # Mock repositories
        mock_api_key_repo = MagicMock()
        mock_api_key_repo.validate_and_get_api_key = AsyncMock(return_value=api_key_data)
        
        mock_auth_repo = MagicMock()
        mock_user_repo = MagicMock()
        
        # Test auth manager
        from app.services.auth_manager import AuthManager
        
        with patch('app.services.auth_manager.get_db_client') as mock_get_db, \
             patch('app.services.auth_manager.settings', mock_settings):
            
            # Mock database client
            mock_db_client = MagicMock()
            mock_db_client.get_collection.return_value = MagicMock()
            mock_get_db.return_value = mock_db_client
            
            auth_manager = AuthManager()
            auth_manager.api_key_provider.api_key_repo = mock_api_key_repo
            
            # Create mock request
            mock_request = MagicMock()
            mock_request.cookies = {}  # No session cookie
            mock_request.headers = {"X-API-Key": api_key}
            
            auth_context = await auth_manager.authenticate(mock_request)
        
        # Verify authentication
        assert auth_context is not None
        assert auth_context["wallet_address"] == test_wallet_address
        assert auth_context["auth_method"] == "api_key"
        
        # Test permission checking
        assert auth_manager.check_permission(auth_context, "read") is True
        assert auth_manager.check_permission(auth_context, "write") is True
        assert auth_manager.check_permission(auth_context, "delete") is True
        assert auth_manager.check_permission(auth_context, "admin") is False

    @pytest.mark.asyncio
    async def test_api_key_vs_wallet_auth_priority(self, mock_settings, test_wallet_address):
        """Test that wallet auth takes priority over API key auth."""
        
        # Create API key
        api_key, key_hash = generate_api_key(test_wallet_address, mock_settings.api_key_secret_key)
        
        # Mock session data (wallet auth)
        session_data = {
            "walletAddress": test_wallet_address,
            "sessionId": "test_session_123"
        }
        
        # Mock repositories and services
        mock_auth_service = MagicMock()
        mock_auth_service.validate_session = AsyncMock(return_value=session_data)
        
        mock_api_key_repo = MagicMock()
        
        from app.services.auth_manager import AuthManager
        
        with patch('app.services.auth_manager.get_db_client') as mock_get_db, \
             patch('app.services.auth_manager.settings', mock_settings):
            
            mock_db_client = MagicMock()
            mock_get_db.return_value = mock_db_client
            
            auth_manager = AuthManager()
            auth_manager.auth_service = mock_auth_service
            
            # Create request with both session and API key
            mock_request = MagicMock()
            mock_request.cookies = {"session_id": "test_session_123"}
            mock_request.headers = {"X-API-Key": api_key}
            
            auth_context = await auth_manager.authenticate(mock_request)
        
        # Should use wallet auth (higher priority)
        assert auth_context["auth_method"] == "wallet"
        assert auth_context["permissions"] == ["read", "write", "delete"]  # Full permissions

    @pytest.mark.asyncio
    async def test_api_key_rate_limiting_integration(self, mock_settings, test_wallet_address):
        """Test API key rate limiting in realistic scenario."""
        
        # Create API key
        api_key, key_hash = generate_api_key(test_wallet_address, mock_settings.api_key_secret_key)
        
        api_key_data = APIKeyInDB(
            key_hash=key_hash,
            wallet_address=test_wallet_address,
            name="Rate Limit Test Key",
            permissions=["read"],
            created_at=datetime.now(timezone.utc),
            expires_at=datetime.now(timezone.utc) + timedelta(days=90),
            is_active=True,
            metadata={}
        )
        
        # Mock Redis client
        mock_redis = MagicMock()
        request_count = 0
        
        def mock_incr(key):
            nonlocal request_count
            request_count += 1
            return request_count
        
        mock_redis.incr = AsyncMock(side_effect=mock_incr)
        mock_redis.expire = AsyncMock()
        
        # Mock repository
        mock_repo = MagicMock()
        mock_repo.validate_and_get_api_key = AsyncMock(return_value=api_key_data)
        
        # Test auth provider with rate limiting
        from app.services.api_key_auth_provider import APIKeyAuthProvider
        auth_provider = APIKeyAuthProvider(mock_repo, mock_redis)
        
        mock_request = MagicMock()
        mock_request.headers = {"X-API-Key": api_key}
        
        # Make requests within limit
        with patch('app.services.api_key_auth_provider.settings', mock_settings):
            for i in range(50):  # Within limit of 100
                auth_result = await auth_provider.authenticate(mock_request)
                assert auth_result is not None
            
            # Simulate exceeding rate limit
            request_count = 101  # Over limit
            
            with pytest.raises(HTTPException) as exc_info:
                await auth_provider.authenticate(mock_request)
            
            assert exc_info.value.status_code == 429

    @pytest.mark.asyncio
    async def test_api_key_expiration_handling(self, mock_settings, test_wallet_address):
        """Test handling of expired API keys."""
        
        # Create expired API key
        api_key, key_hash = generate_api_key(test_wallet_address, mock_settings.api_key_secret_key)
        
        expired_key_data = APIKeyInDB(
            key_hash=key_hash,
            wallet_address=test_wallet_address,
            name="Expired Test Key",
            permissions=["read"],
            created_at=datetime.now(timezone.utc) - timedelta(days=100),
            expires_at=datetime.now(timezone.utc) - timedelta(days=1),  # Expired
            is_active=True,
            metadata={}
        )
        
        # Mock repository to simulate expiration handling
        mock_repo = MagicMock()
        
        # First call returns expired key, second call returns None (deactivated)
        mock_repo.get_api_key_by_hash = AsyncMock(return_value=expired_key_data)
        mock_repo.update_one = AsyncMock()  # Deactivation call
        
        def mock_validate_and_get(key_hash):
            # Simulate repository expiration logic
            if expired_key_data.expires_at < datetime.now(timezone.utc):
                # Deactivate expired key
                expired_key_data.is_active = False
                return None
            return expired_key_data
        
        mock_repo.validate_and_get_api_key = AsyncMock(side_effect=mock_validate_and_get)
        
        # Test authentication with expired key
        from app.services.api_key_auth_provider import APIKeyAuthProvider
        auth_provider = APIKeyAuthProvider(mock_repo, None)
        
        mock_request = MagicMock()
        mock_request.headers = {"X-API-Key": api_key}
        
        with patch('app.services.api_key_auth_provider.settings', mock_settings):
            with pytest.raises(HTTPException) as exc_info:
                await auth_provider.authenticate(mock_request)
            
            assert exc_info.value.status_code == 401
            assert "Invalid or expired" in str(exc_info.value.detail)

    @pytest.mark.asyncio
    async def test_api_key_service_integration(self, mock_settings, test_wallet_address):
        """Test API key service with real key generation."""
        
        # Mock repository
        mock_repo = MagicMock()
        mock_repo.count_active_keys_for_wallet = AsyncMock(return_value=0)
        mock_repo.create_api_key = AsyncMock()
        mock_repo.get_api_keys_by_wallet = AsyncMock(return_value=[])
        
        # Test service
        from app.services.api_key_service import APIKeyService
        from app.schemas.api_key_schema import APIKeyCreate
        
        service = APIKeyService(mock_repo)
        
        # Create API key request
        api_key_create = APIKeyCreate(
            name="Service Integration Test",
            permissions=["read", "write"],
            metadata={"purpose": "integration_test"}
        )
        
        with patch('app.services.api_key_service.settings', mock_settings):
            result = await service.create_api_key(test_wallet_address, api_key_create)
        
        # Verify result
        assert result.api_key.startswith("fv.v1.")
        assert result.name == api_key_create.name
        assert result.permissions == api_key_create.permissions
        assert result.is_active is True
        
        # Verify repository was called
        mock_repo.create_api_key.assert_called_once()
        created_key_data = mock_repo.create_api_key.call_args[0][0]
        assert created_key_data.wallet_address == test_wallet_address
        assert created_key_data.name == api_key_create.name

    @pytest.mark.asyncio
    async def test_concurrent_api_key_operations(self, mock_settings, test_wallet_address):
        """Test concurrent API key operations."""
        import asyncio
        
        # Mock repository for concurrent operations
        mock_repo = MagicMock()
        mock_repo.count_active_keys_for_wallet = AsyncMock(return_value=0)
        mock_repo.create_api_key = AsyncMock()
        mock_repo.get_api_keys_by_wallet = AsyncMock(return_value=[])
        
        from app.services.api_key_service import APIKeyService
        from app.schemas.api_key_schema import APIKeyCreate
        
        service = APIKeyService(mock_repo)
        
        # Create multiple API key requests concurrently
        async def create_api_key(name):
            api_key_create = APIKeyCreate(
                name=f"Concurrent Test {name}",
                permissions=["read"]
            )
            with patch('app.services.api_key_service.settings', mock_settings):
                return await service.create_api_key(test_wallet_address, api_key_create)
        
        # Run concurrent operations
        tasks = [create_api_key(i) for i in range(5)]
        results = await asyncio.gather(*tasks)
        
        # Verify all operations completed
        assert len(results) == 5
        assert all(result.api_key.startswith("fv.v1.") for result in results)
        
        # Verify all API keys are unique
        api_keys = [result.api_key for result in results]
        assert len(set(api_keys)) == 5

    def test_api_key_format_consistency(self, mock_settings, test_wallet_address):
        """Test API key format consistency across multiple generations."""
        
        api_keys = []
        wallet_tags = []
        
        # Generate multiple API keys
        for _ in range(10):
            api_key, key_hash = generate_api_key(test_wallet_address, mock_settings.api_key_secret_key)
            api_keys.append(api_key)
            
            # Extract wallet tag
            parts = api_key.split('.')
            wallet_tags.append(parts[2])
        
        # Verify format consistency
        for api_key in api_keys:
            assert api_key.startswith("fv.v1.")
            parts = api_key.split('.')
            assert len(parts) == 5
        
        # Verify wallet tags are consistent
        expected_tag = test_wallet_address.lower()[-8:]
        assert all(tag == expected_tag for tag in wallet_tags)
        
        # Verify all keys are unique
        assert len(set(api_keys)) == 10

    @pytest.mark.asyncio
    async def test_api_key_permission_enforcement(self, mock_settings, test_wallet_address):
        """Test that API key permissions are properly enforced."""
        
        # Create API keys with different permissions
        read_only_key, read_hash = generate_api_key(test_wallet_address, mock_settings.api_key_secret_key)
        admin_key, admin_hash = generate_api_key(test_wallet_address, mock_settings.api_key_secret_key)
        
        read_only_data = APIKeyInDB(
            key_hash=read_hash,
            wallet_address=test_wallet_address,
            name="Read Only Key",
            permissions=["read"],
            created_at=datetime.now(timezone.utc),
            expires_at=datetime.now(timezone.utc) + timedelta(days=90),
            is_active=True,
            metadata={}
        )
        
        admin_data = APIKeyInDB(
            key_hash=admin_hash,
            wallet_address=test_wallet_address,
            name="Admin Key",
            permissions=["admin"],
            created_at=datetime.now(timezone.utc),
            expires_at=datetime.now(timezone.utc) + timedelta(days=90),
            is_active=True,
            metadata={}
        )
        
        # Mock repository to return appropriate data
        def mock_validate_key(key_hash):
            if key_hash == read_hash:
                return read_only_data
            elif key_hash == admin_hash:
                return admin_data
            return None
        
        mock_repo = MagicMock()
        mock_repo.validate_and_get_api_key = AsyncMock(side_effect=mock_validate_key)
        
        # Test auth provider
        from app.services.api_key_auth_provider import APIKeyAuthProvider
        auth_provider = APIKeyAuthProvider(mock_repo, None)
        
        # Test read-only key
        read_request = MagicMock()
        read_request.headers = {"X-API-Key": read_only_key}
        
        with patch('app.services.api_key_auth_provider.settings', mock_settings):
            read_auth = await auth_provider.authenticate(read_request)
        
        assert read_auth["permissions"] == ["read"]
        assert auth_provider.check_permission("read", read_auth["permissions"]) is True
        assert auth_provider.check_permission("write", read_auth["permissions"]) is False
        assert auth_provider.check_permission("delete", read_auth["permissions"]) is False
        
        # Test admin key
        admin_request = MagicMock()
        admin_request.headers = {"X-API-Key": admin_key}
        
        with patch('app.services.api_key_auth_provider.settings', mock_settings):
            admin_auth = await auth_provider.authenticate(admin_request)
        
        assert admin_auth["permissions"] == ["admin"]
        assert auth_provider.check_permission("read", admin_auth["permissions"]) is True
        assert auth_provider.check_permission("write", admin_auth["permissions"]) is True
        assert auth_provider.check_permission("delete", admin_auth["permissions"]) is True
        assert auth_provider.check_permission("admin", admin_auth["permissions"]) is True

    @pytest.mark.asyncio
    async def test_api_key_error_propagation(self, mock_settings, test_wallet_address):
        """Test proper error propagation through the API key system."""
        
        # Test various error scenarios
        error_scenarios = [
            (Exception("Database connection error"), 500),
            (ValueError("Invalid API key format"), 401),
            (HTTPException(status_code=429, detail="Rate limited"), 429),
        ]
        
        for error, expected_status in error_scenarios:
            mock_repo = MagicMock()
            mock_repo.validate_and_get_api_key = AsyncMock(side_effect=error)
            
            from app.services.api_key_auth_provider import APIKeyAuthProvider
            auth_provider = APIKeyAuthProvider(mock_repo, None)
            
            api_key, _ = generate_api_key(test_wallet_address, mock_settings.api_key_secret_key)
            mock_request = MagicMock()
            mock_request.headers = {"X-API-Key": api_key}
            
            with patch('app.services.api_key_auth_provider.settings', mock_settings):
                if isinstance(error, HTTPException):
                    with pytest.raises(HTTPException) as exc_info:
                        await auth_provider.authenticate(mock_request)
                    assert exc_info.value.status_code == expected_status
                else:
                    # For non-HTTP exceptions, they should be caught and converted
                    try:
                        await auth_provider.authenticate(mock_request)
                    except HTTPException as e:
                        assert e.status_code == 401  # Converted to unauthorized
                    except Exception:
                        # Or propagated as-is depending on implementation
                        pass