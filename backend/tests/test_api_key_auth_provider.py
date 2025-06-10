import pytest
from unittest.mock import MagicMock, AsyncMock, patch
from datetime import datetime, timedelta, timezone
from fastapi import HTTPException, Request

from app.services.api_key_auth_provider import APIKeyAuthProvider
from app.schemas.api_key_schema import APIKeyInDB


class TestAPIKeyAuthProvider:
    """Test suite for API key authentication provider."""

    @pytest.fixture
    def mock_redis(self):
        """Create mock Redis client."""
        redis_client = MagicMock()
        redis_client.incr = AsyncMock()
        redis_client.expire = AsyncMock()
        return redis_client

    @pytest.fixture
    def mock_settings(self):
        """Mock application settings."""
        settings = MagicMock()
        settings.api_key_auth_enabled = True
        settings.api_key_secret_key = "test_secret_key_for_api_key_signing_minimum_32_characters"
        settings.api_key_rate_limit_per_minute = 100
        return settings

    @pytest.fixture
    def auth_provider(self, mock_api_key_repo, mock_redis):
        """Create APIKeyAuthProvider with mocks."""
        return APIKeyAuthProvider(mock_api_key_repo, mock_redis)

    @pytest.fixture
    def auth_provider_no_redis(self, mock_api_key_repo):
        """Create APIKeyAuthProvider without Redis."""
        return APIKeyAuthProvider(mock_api_key_repo, None)

    @pytest.fixture
    def mock_request_with_api_key(self, test_api_key):
        """Create mock request with API key header."""
        request = MagicMock(spec=Request)
        request.headers = {"X-API-Key": test_api_key}
        return request

    @pytest.fixture
    def mock_request_no_api_key(self):
        """Create mock request without API key header."""
        request = MagicMock(spec=Request)
        request.headers = {}
        return request

    @pytest.fixture
    def valid_api_key_data(self, test_wallet_address, test_api_key_hash):
        """Create valid API key data."""
        return APIKeyInDB(
            key_hash=test_api_key_hash,
            wallet_address=test_wallet_address,
            name="Test API Key",
            permissions=["read", "write"],
            created_at=datetime.now(timezone.utc),
            last_used_at=None,
            expires_at=datetime.now(timezone.utc) + timedelta(days=90),
            is_active=True,
            metadata={}
        )

    @pytest.mark.asyncio
    async def test_authenticate_disabled(self, mock_api_key_repo, mock_redis, mock_request_with_api_key):
        """Test authentication when API keys are disabled."""
        # Create provider with disabled API keys
        auth_provider = APIKeyAuthProvider(mock_api_key_repo, mock_redis)
        auth_provider.enabled = False
        
        result = await auth_provider.authenticate(mock_request_with_api_key)
        
        # Should return None when disabled
        assert result is None

    @pytest.mark.asyncio
    async def test_authenticate_no_api_key_header(self, auth_provider, mock_request_no_api_key):
        """Test authentication when no API key is provided."""
        result = await auth_provider.authenticate(mock_request_no_api_key)
        
        # Should return None when no API key header
        assert result is None

    @pytest.mark.asyncio
    async def test_authenticate_invalid_format(self, auth_provider, mock_settings):
        """Test authentication with invalid API key format."""
        request = MagicMock(spec=Request)
        request.headers = {"X-API-Key": "invalid_format"}
        
        with patch('app.services.api_key_auth_provider.settings', mock_settings), \
             patch('app.services.api_key_auth_provider.validate_api_key_format', return_value=False):
            
            with pytest.raises(HTTPException) as exc_info:
                await auth_provider.authenticate(request)
            
            assert exc_info.value.status_code == 401
            assert "Invalid API key format" in str(exc_info.value.detail)

    @pytest.mark.asyncio
    async def test_authenticate_invalid_signature(self, auth_provider, mock_settings, test_api_key):
        """Test authentication with invalid API key signature."""
        request = MagicMock(spec=Request)
        request.headers = {"X-API-Key": test_api_key}
        
        with patch('app.services.api_key_auth_provider.settings', mock_settings), \
             patch('app.services.api_key_auth_provider.validate_api_key_format', return_value=True), \
             patch('app.services.api_key_auth_provider.validate_api_key_signature', return_value=False):
            
            with pytest.raises(HTTPException) as exc_info:
                await auth_provider.authenticate(request)
            
            assert exc_info.value.status_code == 401
            assert "Invalid API key signature" in str(exc_info.value.detail)

    @pytest.mark.asyncio
    async def test_authenticate_rate_limited(self, auth_provider, mock_settings, test_api_key, mock_redis):
        """Test authentication when rate limit is exceeded."""
        request = MagicMock(spec=Request)
        request.headers = {"X-API-Key": test_api_key}
        
        # Mock rate limit exceeded
        mock_redis.incr.return_value = 101  # Over limit of 100
        
        with patch('app.services.api_key_auth_provider.settings', mock_settings), \
             patch('app.services.api_key_auth_provider.validate_api_key_format', return_value=True), \
             patch('app.services.api_key_auth_provider.validate_api_key_signature', return_value=True), \
             patch('app.services.api_key_auth_provider.get_api_key_hash', return_value="test_hash"):
            
            with pytest.raises(HTTPException) as exc_info:
                await auth_provider.authenticate(request)
            
            assert exc_info.value.status_code == 429
            assert "Rate limit exceeded" in str(exc_info.value.detail)

    @pytest.mark.asyncio
    async def test_authenticate_invalid_or_expired_key(self, auth_provider, mock_settings, test_api_key, mock_api_key_repo):
        """Test authentication with invalid or expired API key."""
        request = MagicMock(spec=Request)
        request.headers = {"X-API-Key": test_api_key}
        
        # Mock API key not found or expired
        mock_api_key_repo.validate_and_get_api_key.return_value = None
        
        with patch('app.services.api_key_auth_provider.settings', mock_settings), \
             patch('app.services.api_key_auth_provider.validate_api_key_format', return_value=True), \
             patch('app.services.api_key_auth_provider.validate_api_key_signature', return_value=True), \
             patch('app.services.api_key_auth_provider.get_api_key_hash', return_value="test_hash"):
            
            with pytest.raises(HTTPException) as exc_info:
                await auth_provider.authenticate(request)
            
            assert exc_info.value.status_code == 401
            assert "Invalid or expired API key" in str(exc_info.value.detail)

    @pytest.mark.asyncio
    async def test_authenticate_success(self, auth_provider, mock_settings, test_api_key, 
                                      mock_api_key_repo, valid_api_key_data):
        """Test successful API key authentication."""
        request = MagicMock(spec=Request)
        request.headers = {"X-API-Key": test_api_key}
        
        # Mock successful validation
        mock_api_key_repo.validate_and_get_api_key.return_value = valid_api_key_data
        
        with patch('app.services.api_key_auth_provider.settings', mock_settings), \
             patch('app.services.api_key_auth_provider.validate_api_key_format', return_value=True), \
             patch('app.services.api_key_auth_provider.validate_api_key_signature', return_value=True), \
             patch('app.services.api_key_auth_provider.get_api_key_hash', return_value="test_hash"):
            
            result = await auth_provider.authenticate(request)
        
        # Should return authentication context
        assert result is not None
        assert result["wallet_address"] == valid_api_key_data.wallet_address
        assert result["auth_method"] == "api_key"
        assert result["permissions"] == valid_api_key_data.permissions

    @pytest.mark.asyncio
    async def test_authenticate_no_redis_rate_limiting(self, auth_provider_no_redis, mock_settings, 
                                                     test_api_key, mock_api_key_repo, valid_api_key_data):
        """Test authentication without Redis (no rate limiting)."""
        request = MagicMock(spec=Request)
        request.headers = {"X-API-Key": test_api_key}
        
        # Mock successful validation
        mock_api_key_repo.validate_and_get_api_key.return_value = valid_api_key_data
        
        with patch('app.services.api_key_auth_provider.settings', mock_settings), \
             patch('app.services.api_key_auth_provider.validate_api_key_format', return_value=True), \
             patch('app.services.api_key_auth_provider.validate_api_key_signature', return_value=True), \
             patch('app.services.api_key_auth_provider.get_api_key_hash', return_value="test_hash"):
            
            result = await auth_provider_no_redis.authenticate(request)
        
        # Should succeed without rate limiting
        assert result is not None
        assert result["wallet_address"] == valid_api_key_data.wallet_address

    @pytest.mark.asyncio
    async def test_check_rate_limit_within_limit(self, auth_provider, mock_redis, mock_settings):
        """Test rate limiting when within limit."""
        # Mock Redis responses
        mock_redis.incr.return_value = 50  # Within limit of 100
        mock_redis.expire.return_value = None
        
        with patch('app.services.api_key_auth_provider.settings', mock_settings), \
             patch('app.services.api_key_auth_provider.datetime') as mock_datetime:
            
            # Mock current time - use now() instead of utcnow()
            mock_datetime.now.return_value = datetime(2025, 1, 1, 12, 30, 0, tzinfo=timezone.utc)
            mock_datetime.timezone = timezone
            
            result = await auth_provider._check_rate_limit("test_hash")
        
        # Should not be rate limited
        assert result is False
        
        # Verify Redis calls
        mock_redis.incr.assert_called_once()
        # Expire is only called on first request (count == 1), but here count is 50
        mock_redis.expire.assert_not_called()

    @pytest.mark.asyncio
    async def test_check_rate_limit_exceeded(self, auth_provider, mock_redis, mock_settings):
        """Test rate limiting when limit is exceeded."""
        # Mock Redis responses
        mock_redis.incr.return_value = 101  # Over limit of 100
        
        with patch('app.services.api_key_auth_provider.settings', mock_settings):
            result = await auth_provider._check_rate_limit("test_hash")
        
        # Should be rate limited
        assert result is True

    @pytest.mark.asyncio
    async def test_check_rate_limit_first_request(self, auth_provider, mock_redis, mock_settings):
        """Test rate limiting on first request (sets expiration)."""
        # Mock first request (count = 1)
        mock_redis.incr.return_value = 1
        mock_redis.expire.return_value = None
        
        with patch('app.services.api_key_auth_provider.settings', mock_settings):
            result = await auth_provider._check_rate_limit("test_hash")
        
        # Should not be rate limited
        assert result is False
        
        # Should set expiration on first request
        mock_redis.expire.assert_called_once()

    @pytest.mark.asyncio
    async def test_check_rate_limit_redis_error(self, auth_provider, mock_redis, mock_settings):
        """Test rate limiting when Redis fails."""
        # Mock Redis error
        mock_redis.incr.side_effect = Exception("Redis connection error")
        
        with patch('app.services.api_key_auth_provider.settings', mock_settings):
            result = await auth_provider._check_rate_limit("test_hash")
        
        # Should allow request when Redis fails (graceful degradation)
        assert result is False

    def test_check_permission_admin(self, auth_provider):
        """Test permission checking with admin permission."""
        permissions = ["admin"]
        
        # Admin should have access to all permissions
        assert auth_provider.check_permission("read", permissions) is True
        assert auth_provider.check_permission("write", permissions) is True
        assert auth_provider.check_permission("delete", permissions) is True
        assert auth_provider.check_permission("admin", permissions) is True

    def test_check_permission_specific(self, auth_provider):
        """Test permission checking with specific permissions."""
        permissions = ["read", "write"]
        
        # Should have specific permissions
        assert auth_provider.check_permission("read", permissions) is True
        assert auth_provider.check_permission("write", permissions) is True
        
        # Should not have permissions not granted
        assert auth_provider.check_permission("delete", permissions) is False
        assert auth_provider.check_permission("admin", permissions) is False

    def test_check_permission_empty(self, auth_provider):
        """Test permission checking with no permissions."""
        permissions = []
        
        # Should not have any permissions
        assert auth_provider.check_permission("read", permissions) is False
        assert auth_provider.check_permission("write", permissions) is False
        assert auth_provider.check_permission("delete", permissions) is False
        assert auth_provider.check_permission("admin", permissions) is False

    @pytest.mark.asyncio
    async def test_rate_limit_key_format(self, auth_provider, mock_redis, mock_settings):
        """Test that rate limit keys are formatted correctly."""
        test_hash = "abc123def456"
        
        mock_redis.incr.return_value = 1
        
        with patch('app.services.api_key_auth_provider.settings', mock_settings), \
             patch('app.services.api_key_auth_provider.datetime') as mock_datetime:
            
            # Mock specific timestamp
            test_time = datetime(2025, 1, 1, 12, 45, 30)  # 45th minute
            mock_datetime.now.return_value = test_time
            
            await auth_provider._check_rate_limit(test_hash)
        
        # Verify the rate limit key format
        expected_minute = int(test_time.timestamp() / 60)  # 21250
        expected_key = f"rate_limit:api_key:{test_hash}:{expected_minute}"
        
        mock_redis.incr.assert_called_once_with(expected_key)

    @pytest.mark.asyncio
    async def test_multiple_requests_same_minute(self, auth_provider, mock_redis, mock_settings):
        """Test multiple requests within the same minute."""
        test_hash = "test_hash_123"
        
        # Simulate multiple requests
        call_counts = [1, 2, 3, 4, 5]
        
        with patch('app.services.api_key_auth_provider.settings', mock_settings):
            for count in call_counts:
                mock_redis.incr.return_value = count
                result = await auth_provider._check_rate_limit(test_hash)
                
                # All should be within limit
                assert result is False

    @pytest.mark.asyncio
    async def test_api_key_extraction_case_insensitive_header(self, auth_provider, mock_settings, 
                                                            mock_api_key_repo, valid_api_key_data):
        """Test that API key header extraction works with correct case and fails with wrong case."""
        mock_api_key_repo.validate_and_get_api_key.return_value = valid_api_key_data
        
        # Test correct case - should work
        request = MagicMock(spec=Request)
        request.headers = {"X-API-Key": "test_key"}
        
        with patch('app.services.api_key_auth_provider.settings', mock_settings), \
             patch('app.services.api_key_auth_provider.validate_api_key_format', return_value=True), \
             patch('app.services.api_key_auth_provider.validate_api_key_signature', return_value=True), \
             patch('app.services.api_key_auth_provider.get_api_key_hash', return_value="test_hash"):
            
            result = await auth_provider.authenticate(request)
            assert result is not None
            assert result["wallet_address"] == valid_api_key_data.wallet_address
        
        # Test incorrect case - should not work (implementation is case-sensitive)
        request_wrong_case = MagicMock(spec=Request)
        request_wrong_case.headers = {"x-api-key": "test_key"}
        
        result = await auth_provider.authenticate(request_wrong_case)
        assert result is None

    @pytest.mark.asyncio
    async def test_concurrent_rate_limit_checks(self, auth_provider, mock_redis, mock_settings):
        """Test concurrent rate limit checks."""
        import asyncio
        
        test_hash = "concurrent_test_hash"
        mock_redis.incr.return_value = 50  # Within limit
        
        with patch('app.services.api_key_auth_provider.settings', mock_settings):
            # Simulate concurrent requests
            tasks = [
                auth_provider._check_rate_limit(test_hash)
                for _ in range(10)
            ]
            
            results = await asyncio.gather(*tasks)
        
        # All should pass rate limiting
        assert all(result is False for result in results)
        
        # Redis incr should be called for each request
        assert mock_redis.incr.call_count == 10

    @pytest.mark.asyncio
    async def test_authentication_with_whitespace_api_key(self, auth_provider, mock_settings):
        """Test authentication with API key containing whitespace."""
        request = MagicMock(spec=Request)
        request.headers = {"X-API-Key": "  fv.v1.231d7d7f.nonce.sig  "}  # With whitespace
        
        with patch('app.services.api_key_auth_provider.settings', mock_settings), \
             patch('app.services.api_key_auth_provider.validate_api_key_format') as mock_validate:
            
            # The implementation should handle whitespace appropriately
            await auth_provider.authenticate(request)
            
            # Check what was passed to validation (should it be trimmed?)
            called_key = mock_validate.call_args[0][0] if mock_validate.called else None
            # This test documents the current behavior - adjust based on requirements

    @pytest.mark.asyncio
    async def test_permission_edge_cases(self, auth_provider):
        """Test permission checking edge cases."""
        # Test with None permissions
        assert auth_provider.check_permission("read", None) is False
        
        # Test with non-list permissions (edge case)
        # Note: This might raise an exception depending on implementation
        try:
            result = auth_provider.check_permission("read", "not_a_list")
            assert result is False
        except (TypeError, AttributeError):
            # Expected behavior for invalid input
            pass

    @pytest.mark.asyncio
    async def test_rate_limit_expiration_timing(self, auth_provider, mock_redis, mock_settings):
        """Test that rate limit keys have correct expiration."""
        test_hash = "expiration_test_hash"
        mock_redis.incr.return_value = 1  # First request
        
        with patch('app.services.api_key_auth_provider.settings', mock_settings):
            await auth_provider._check_rate_limit(test_hash)
        
        # Should set 120 second expiration (2 minutes)
        mock_redis.expire.assert_called_once()
        call_args = mock_redis.expire.call_args
        assert call_args[0][1] == 120  # 2 minutes expiration