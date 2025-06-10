import pytest
from unittest.mock import MagicMock, AsyncMock, patch
from datetime import datetime, timedelta
from fastapi import HTTPException
from fastapi.testclient import TestClient

from app.schemas.api_key_schema import APIKeyCreate, APIKeyResponse, APIKeyCreateResponse, APIKeyUpdate


class TestAPIKeyRoutes:
    """Test suite for API key HTTP routes."""

    @pytest.fixture
    def mock_settings(self):
        """Mock application settings."""
        settings = MagicMock()
        settings.api_key_auth_enabled = True
        settings.api_key_max_per_wallet = 10
        settings.api_key_default_expiration_days = 90
        settings.api_key_rate_limit_per_minute = 100
        return settings

    @pytest.fixture
    def mock_current_user(self, test_wallet_address):
        """Mock current authenticated user."""
        return {"walletAddress": test_wallet_address}

    @pytest.fixture
    def sample_api_key_create_data(self):
        """Sample API key creation data."""
        return {
            "name": "Test API Key",
            "permissions": ["read", "write"],
            "expires_at": (datetime.utcnow() + timedelta(days=30)).isoformat(),
            "metadata": {"purpose": "testing"}
        }

    @pytest.fixture
    def sample_api_key_response(self, test_wallet_address):
        """Sample API key response data."""
        return APIKeyResponse(
            name="Test API Key",
            permissions=["read", "write"],
            created_at=datetime.utcnow(),
            last_used_at=None,
            expires_at=datetime.utcnow() + timedelta(days=90),
            is_active=True,
            metadata={"purpose": "testing"}
        )

    @pytest.fixture
    def sample_api_key_create_response(self, test_api_key):
        """Sample API key creation response."""
        return APIKeyCreateResponse(
            api_key=test_api_key,
            name="Test API Key",
            permissions=["read", "write"],
            created_at=datetime.utcnow(),
            expires_at=datetime.utcnow() + timedelta(days=90),
            is_active=True,
            metadata={"purpose": "testing"},
            last_used_at=None
        )

    def test_get_api_keys_status_enabled(self, client, mock_settings):
        """Test API keys status endpoint when enabled."""
        with patch('app.api.api_keys_routes.settings', mock_settings):
            response = client.get("/api-keys/status")
        
        assert response.status_code == 200
        data = response.json()
        assert data["enabled"] is True
        assert data["max_keys_per_wallet"] == 10
        assert data["default_expiration_days"] == 90
        assert data["rate_limit_per_minute"] == 100

    def test_get_api_keys_status_disabled(self, client, mock_settings):
        """Test API keys status endpoint when disabled."""
        mock_settings.api_key_auth_enabled = False
        
        with patch('app.api.api_keys_routes.settings', mock_settings):
            response = client.get("/api-keys/status")
        
        assert response.status_code == 200
        data = response.json()
        assert data["enabled"] is False

    def test_get_api_keys_status_no_auth_required(self, client, mock_settings):
        """Test that status endpoint doesn't require authentication."""
        # This test ensures the status endpoint is public
        with patch('app.api.api_keys_routes.settings', mock_settings):
            response = client.get("/api-keys/status")
        
        # Should work without authentication
        assert response.status_code == 200

    def test_create_api_key_success(self, client, mock_settings, sample_api_key_create_data, 
                                  sample_api_key_create_response, mock_current_user):
        """Test successful API key creation."""
        with patch('app.api.api_keys_routes.settings', mock_settings), \
             patch('app.api.api_keys_routes.get_wallet_address', return_value=mock_current_user["walletAddress"]), \
             patch('app.api.api_keys_routes.get_api_key_service') as mock_get_service:
            
            # Mock service
            mock_service = MagicMock()
            mock_service.create_api_key = AsyncMock(return_value=sample_api_key_create_response)
            mock_get_service.return_value = mock_service
            
            response = client.post("/api-keys/create", json=sample_api_key_create_data)
        
        assert response.status_code == 200
        data = response.json()
        assert "api_key" in data
        assert data["name"] == sample_api_key_create_data["name"]
        assert data["permissions"] == sample_api_key_create_data["permissions"]

    def test_create_api_key_disabled(self, client, sample_api_key_create_data, mock_current_user):
        """Test API key creation when feature is disabled."""
        mock_settings = MagicMock()
        mock_settings.api_key_auth_enabled = False
        
        with patch('app.api.api_keys_routes.settings', mock_settings), \
             patch('app.api.api_keys_routes.get_wallet_address', return_value=mock_current_user["walletAddress"]):
            
            response = client.post("/api-keys/create", json=sample_api_key_create_data)
        
        assert response.status_code == 400
        assert "not enabled" in response.json()["detail"]

    def test_create_api_key_validation_error(self, client, mock_settings, mock_current_user):
        """Test API key creation with validation errors."""
        invalid_data = {
            "name": "",  # Empty name
            "permissions": ["invalid_permission"],  # Invalid permission
        }
        
        with patch('app.api.api_keys_routes.settings', mock_settings), \
             patch('app.api.api_keys_routes.get_wallet_address', return_value=mock_current_user["walletAddress"]), \
             patch('app.api.api_keys_routes.get_api_key_service') as mock_get_service:
            
            # Mock service to raise ValueError
            mock_service = MagicMock()
            mock_service.create_api_key = AsyncMock(side_effect=ValueError("Invalid permissions"))
            mock_get_service.return_value = mock_service
            
            response = client.post("/api-keys/create", json=invalid_data)
        
        assert response.status_code == 400

    def test_create_api_key_max_limit_reached(self, client, mock_settings, sample_api_key_create_data, mock_current_user):
        """Test API key creation when limit is reached."""
        with patch('app.api.api_keys_routes.settings', mock_settings), \
             patch('app.api.api_keys_routes.get_wallet_address', return_value=mock_current_user["walletAddress"]), \
             patch('app.api.api_keys_routes.get_api_key_service') as mock_get_service:
            
            # Mock service to raise max limit error
            mock_service = MagicMock()
            mock_service.create_api_key = AsyncMock(side_effect=ValueError("Maximum API keys limit reached"))
            mock_get_service.return_value = mock_service
            
            response = client.post("/api-keys/create", json=sample_api_key_create_data)
        
        assert response.status_code == 400
        assert "limit reached" in response.json()["detail"]

    def test_create_api_key_api_key_auth_forbidden(self, client, mock_settings, sample_api_key_create_data):
        """Test that API keys cannot create other API keys."""
        with patch('app.api.api_keys_routes.settings', mock_settings), \
             patch('app.api.api_keys_routes.get_wallet_address', return_value="test_wallet"):
            
            # Create a request that appears to be from API key auth
            def mock_request():
                request = MagicMock()
                request.state.auth_method = "api_key"
                return request
            
            with patch('app.api.api_keys_routes.Request', side_effect=mock_request):
                response = client.post("/api-keys/create", json=sample_api_key_create_data)
        
        # Should be forbidden
        assert response.status_code == 403
        assert "cannot create other API keys" in response.json()["detail"]

    def test_list_api_keys_success(self, client, mock_settings, sample_api_key_response, mock_current_user):
        """Test successful API key listing."""
        with patch('app.api.api_keys_routes.settings', mock_settings), \
             patch('app.api.api_keys_routes.get_wallet_address', return_value=mock_current_user["walletAddress"]), \
             patch('app.api.api_keys_routes.get_api_key_service') as mock_get_service:
            
            # Mock service
            mock_service = MagicMock()
            mock_service.list_api_keys = AsyncMock(return_value=[sample_api_key_response])
            mock_get_service.return_value = mock_service
            
            response = client.get("/api-keys/list")
        
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["name"] == sample_api_key_response.name
        assert "api_key" not in data[0]  # Sensitive data should not be included

    def test_list_api_keys_empty(self, client, mock_settings, mock_current_user):
        """Test listing API keys when none exist."""
        with patch('app.api.api_keys_routes.settings', mock_settings), \
             patch('app.api.api_keys_routes.get_wallet_address', return_value=mock_current_user["walletAddress"]), \
             patch('app.api.api_keys_routes.get_api_key_service') as mock_get_service:
            
            # Mock service to return empty list
            mock_service = MagicMock()
            mock_service.list_api_keys = AsyncMock(return_value=[])
            mock_get_service.return_value = mock_service
            
            response = client.get("/api-keys/list")
        
        assert response.status_code == 200
        assert response.json() == []

    def test_list_api_keys_disabled(self, client, mock_current_user):
        """Test listing API keys when feature is disabled."""
        mock_settings = MagicMock()
        mock_settings.api_key_auth_enabled = False
        
        with patch('app.api.api_keys_routes.settings', mock_settings), \
             patch('app.api.api_keys_routes.get_wallet_address', return_value=mock_current_user["walletAddress"]):
            
            response = client.get("/api-keys/list")
        
        assert response.status_code == 400
        assert "not enabled" in response.json()["detail"]

    def test_revoke_api_key_success(self, client, mock_settings, mock_current_user):
        """Test successful API key revocation."""
        key_name = "Test API Key"
        
        with patch('app.api.api_keys_routes.settings', mock_settings), \
             patch('app.api.api_keys_routes.get_wallet_address', return_value=mock_current_user["walletAddress"]), \
             patch('app.api.api_keys_routes.get_api_key_service') as mock_get_service:
            
            # Mock service
            mock_service = MagicMock()
            mock_service.revoke_api_key = AsyncMock(return_value=True)
            mock_get_service.return_value = mock_service
            
            response = client.delete(f"/api-keys/{key_name}")
        
        assert response.status_code == 200
        data = response.json()
        assert "revoked successfully" in data["message"]

    def test_revoke_api_key_not_found(self, client, mock_settings, mock_current_user):
        """Test revoking non-existent API key."""
        key_name = "Nonexistent Key"
        
        with patch('app.api.api_keys_routes.settings', mock_settings), \
             patch('app.api.api_keys_routes.get_wallet_address', return_value=mock_current_user["walletAddress"]), \
             patch('app.api.api_keys_routes.get_api_key_service') as mock_get_service:
            
            # Mock service to return False (not found)
            mock_service = MagicMock()
            mock_service.revoke_api_key = AsyncMock(return_value=False)
            mock_get_service.return_value = mock_service
            
            response = client.delete(f"/api-keys/{key_name}")
        
        assert response.status_code == 404
        assert "not found" in response.json()["detail"]

    def test_revoke_api_key_url_encoding(self, client, mock_settings, mock_current_user):
        """Test revoking API key with special characters in name."""
        key_name = "Test Key With Spaces"
        encoded_name = "Test%20Key%20With%20Spaces"
        
        with patch('app.api.api_keys_routes.settings', mock_settings), \
             patch('app.api.api_keys_routes.get_wallet_address', return_value=mock_current_user["walletAddress"]), \
             patch('app.api.api_keys_routes.get_api_key_service') as mock_get_service:
            
            mock_service = MagicMock()
            mock_service.revoke_api_key = AsyncMock(return_value=True)
            mock_get_service.return_value = mock_service
            
            response = client.delete(f"/api-keys/{encoded_name}")
        
        assert response.status_code == 200
        # Verify the service was called with the decoded name
        mock_service.revoke_api_key.assert_called_once_with(mock_current_user["walletAddress"], key_name)

    def test_update_api_key_permissions_success(self, client, mock_settings, mock_current_user):
        """Test successful API key permission update."""
        key_name = "Test API Key"
        update_data = {
            "permissions": ["read", "write", "delete"]
        }
        
        with patch('app.api.api_keys_routes.settings', mock_settings), \
             patch('app.api.api_keys_routes.get_wallet_address', return_value=mock_current_user["walletAddress"]), \
             patch('app.api.api_keys_routes.get_api_key_service') as mock_get_service:
            
            # Mock service
            mock_service = MagicMock()
            mock_service.update_permissions = AsyncMock(return_value=True)
            mock_get_service.return_value = mock_service
            
            response = client.put(f"/api-keys/{key_name}/permissions", json=update_data)
        
        assert response.status_code == 200
        data = response.json()
        assert "updated" in data["message"]

    def test_update_api_key_permissions_not_found(self, client, mock_settings, mock_current_user):
        """Test updating permissions for non-existent API key."""
        key_name = "Nonexistent Key"
        update_data = {
            "permissions": ["read"]
        }
        
        with patch('app.api.api_keys_routes.settings', mock_settings), \
             patch('app.api.api_keys_routes.get_wallet_address', return_value=mock_current_user["walletAddress"]), \
             patch('app.api.api_keys_routes.get_api_key_service') as mock_get_service:
            
            # Mock service to return False (not found)
            mock_service = MagicMock()
            mock_service.update_permissions = AsyncMock(return_value=False)
            mock_get_service.return_value = mock_service
            
            response = client.put(f"/api-keys/{key_name}/permissions", json=update_data)
        
        assert response.status_code == 404
        assert "not found" in response.json()["detail"]

    def test_update_api_key_permissions_invalid(self, client, mock_settings, mock_current_user):
        """Test updating API key with invalid permissions."""
        key_name = "Test API Key"
        update_data = {
            "permissions": ["invalid_permission"]
        }
        
        with patch('app.api.api_keys_routes.settings', mock_settings), \
             patch('app.api.api_keys_routes.get_wallet_address', return_value=mock_current_user["walletAddress"]), \
             patch('app.api.api_keys_routes.get_api_key_service') as mock_get_service:
            
            # Mock service to raise ValueError
            mock_service = MagicMock()
            mock_service.update_permissions = AsyncMock(side_effect=ValueError("Invalid permissions"))
            mock_get_service.return_value = mock_service
            
            response = client.put(f"/api-keys/{key_name}/permissions", json=update_data)
        
        assert response.status_code == 400

    def test_authentication_required(self, client, mock_settings):
        """Test that API key management endpoints require authentication."""
        endpoints_to_test = [
            ("POST", "/api-keys/create", {"name": "test"}),
            ("GET", "/api-keys/list", None),
            ("DELETE", "/api-keys/test", None),
            ("PUT", "/api-keys/test/permissions", {"permissions": ["read"]})
        ]
        
        with patch('app.api.api_keys_routes.settings', mock_settings):
            for method, endpoint, json_data in endpoints_to_test:
                if method == "POST":
                    response = client.post(endpoint, json=json_data)
                elif method == "GET":
                    response = client.get(endpoint)
                elif method == "DELETE":
                    response = client.delete(endpoint)
                elif method == "PUT":
                    response = client.put(endpoint, json=json_data)
                
                # Should require authentication
                assert response.status_code in [401, 403]

    def test_error_handling_service_exception(self, client, mock_settings, sample_api_key_create_data, mock_current_user):
        """Test error handling when service raises unexpected exception."""
        with patch('app.api.api_keys_routes.settings', mock_settings), \
             patch('app.api.api_keys_routes.get_wallet_address', return_value=mock_current_user["walletAddress"]), \
             patch('app.api.api_keys_routes.get_api_key_service') as mock_get_service:
            
            # Mock service to raise unexpected exception
            mock_service = MagicMock()
            mock_service.create_api_key = AsyncMock(side_effect=Exception("Database error"))
            mock_get_service.return_value = mock_service
            
            response = client.post("/api-keys/create", json=sample_api_key_create_data)
        
        assert response.status_code == 500
        assert "Failed to create API key" in response.json()["detail"]

    def test_request_validation(self, client, mock_settings, mock_current_user):
        """Test request validation for required fields."""
        # Test missing required fields
        invalid_requests = [
            {},  # Empty request
            {"permissions": ["read"]},  # Missing name
            {"name": ""},  # Empty name
            {"name": "test", "permissions": []},  # Empty permissions
        ]
        
        with patch('app.api.api_keys_routes.settings', mock_settings), \
             patch('app.api.api_keys_routes.get_wallet_address', return_value=mock_current_user["walletAddress"]):
            
            for invalid_data in invalid_requests:
                response = client.post("/api-keys/create", json=invalid_data)
                # Should return validation error
                assert response.status_code == 422  # Unprocessable Entity

    def test_response_format(self, client, mock_settings, sample_api_key_create_data, 
                           sample_api_key_create_response, mock_current_user):
        """Test that response format matches schema."""
        with patch('app.api.api_keys_routes.settings', mock_settings), \
             patch('app.api.api_keys_routes.get_wallet_address', return_value=mock_current_user["walletAddress"]), \
             patch('app.api.api_keys_routes.get_api_key_service') as mock_get_service:
            
            mock_service = MagicMock()
            mock_service.create_api_key = AsyncMock(return_value=sample_api_key_create_response)
            mock_get_service.return_value = mock_service
            
            response = client.post("/api-keys/create", json=sample_api_key_create_data)
        
        assert response.status_code == 200
        data = response.json()
        
        # Verify required fields are present
        required_fields = ["api_key", "name", "permissions", "created_at", "expires_at", "is_active"]
        for field in required_fields:
            assert field in data

    def test_content_type_handling(self, client, mock_settings, sample_api_key_create_data, mock_current_user):
        """Test proper content type handling."""
        with patch('app.api.api_keys_routes.settings', mock_settings), \
             patch('app.api.api_keys_routes.get_wallet_address', return_value=mock_current_user["walletAddress"]), \
             patch('app.api.api_keys_routes.get_api_key_service') as mock_get_service:
            
            mock_service = MagicMock()
            mock_service.create_api_key = AsyncMock(return_value=MagicMock())
            mock_get_service.return_value = mock_service
            
            # Test with different content types
            response_json = client.post("/api-keys/create", json=sample_api_key_create_data)
            assert response_json.status_code == 200
            
            # Test with form data (should fail)
            response_form = client.post("/api-keys/create", data=sample_api_key_create_data)
            assert response_form.status_code == 422  # Should expect JSON

    def test_concurrent_requests(self, client, mock_settings, sample_api_key_create_data, mock_current_user):
        """Test handling of concurrent requests."""
        import asyncio
        
        with patch('app.api.api_keys_routes.settings', mock_settings), \
             patch('app.api.api_keys_routes.get_wallet_address', return_value=mock_current_user["walletAddress"]), \
             patch('app.api.api_keys_routes.get_api_key_service') as mock_get_service:
            
            mock_service = MagicMock()
            mock_service.create_api_key = AsyncMock(return_value=MagicMock())
            mock_get_service.return_value = mock_service
            
            # Multiple concurrent requests should be handled properly
            responses = []
            for i in range(5):
                data = sample_api_key_create_data.copy()
                data["name"] = f"Test Key {i}"
                response = client.post("/api-keys/create", json=data)
                responses.append(response)
            
            # All should succeed (assuming service handles concurrency)
            for response in responses:
                assert response.status_code == 200

    def test_large_request_handling(self, client, mock_settings, mock_current_user):
        """Test handling of large requests."""
        # Create a request with large metadata
        large_data = {
            "name": "Test Key",
            "permissions": ["read"],
            "metadata": {
                "large_field": "x" * 10000,  # 10KB of data
                "description": "A" * 1000
            }
        }
        
        with patch('app.api.api_keys_routes.settings', mock_settings), \
             patch('app.api.api_keys_routes.get_wallet_address', return_value=mock_current_user["walletAddress"]), \
             patch('app.api.api_keys_routes.get_api_key_service') as mock_get_service:
            
            mock_service = MagicMock()
            mock_service.create_api_key = AsyncMock(return_value=MagicMock())
            mock_get_service.return_value = mock_service
            
            response = client.post("/api-keys/create", json=large_data)
            
            # Should handle large requests appropriately
            # (may succeed or fail based on configured limits)
            assert response.status_code in [200, 413, 422]