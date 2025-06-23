import pytest
from unittest.mock import MagicMock, AsyncMock, patch
from fastapi import HTTPException
from fastapi.testclient import TestClient

from app.config import settings


class TestDelegationRoutes:
    """Test suite for delegation HTTP routes."""

    @pytest.fixture
    def mock_auth_bypass(self, mock_current_user):
        """Mock authentication to bypass auth for tests."""
        def auth_bypass():
            # Mock the auth manager to return successful authentication
            mock_auth_context = {
                "wallet_address": mock_current_user["walletAddress"],
                "auth_method": "wallet",
                "permissions": ["read", "write", "delete"]
            }
            return patch('app.utilities.auth_middleware.AuthManager.authenticate', 
                        new_callable=AsyncMock, return_value=mock_auth_context)
        return auth_bypass

    @pytest.fixture
    def mock_blockchain_service(self):
        """Mock blockchain service for testing."""
        mock_service = MagicMock()
        mock_service.check_delegation = AsyncMock(return_value=False)
        mock_service.transaction_builder = MagicMock()
        mock_service.transaction_builder.build_set_delegate_transaction = AsyncMock(
            return_value={
                "success": True,
                "transaction": {
                    "to": "0x123456789",
                    "data": "0xabcdef",
                    "gas": 150000,
                    "gasPrice": 20000000000,
                    "chainId": 11155111,
                    "nonce": 10
                },
                "estimated_gas": 150000,
                "gas_price": 20000000000,
                "function_name": "setDelegate"
            }
        )
        return mock_service

    def setup_dependency_overrides(self, mock_blockchain_service=None, wallet_address=None):
        """Helper to setup FastAPI dependency overrides."""
        from app.api.delegation_routes import get_blockchain_service, get_wallet_address
        from app.main import app
        
        if mock_blockchain_service:
            app.dependency_overrides[get_blockchain_service] = lambda: mock_blockchain_service
        if wallet_address:
            app.dependency_overrides[get_wallet_address] = lambda: wallet_address
        
        return app

    def cleanup_dependency_overrides(self):
        """Clean up FastAPI dependency overrides."""
        from app.main import app
        app.dependency_overrides.clear()

    @pytest.mark.asyncio
    async def test_server_info_public_access(self):
        """Test that server info endpoint is publicly accessible."""
        from app.main import app
        
        with TestClient(app) as client:
            response = client.get("/delegation/server-info")
            
        assert response.status_code == 200
        data = response.json()
        assert "server_wallet_address" in data
        assert data["server_wallet_address"] == settings.wallet_address
        assert "network" in data
        assert "features" in data
        assert data["network"]["chain_id"] == 11155111
        assert data["network"]["network_name"] == "Sepolia Testnet"

    @pytest.mark.asyncio
    async def test_delegation_status_requires_auth(self):
        """Test that delegation status requires authentication."""
        from app.main import app
        
        with TestClient(app) as client:
            response = client.get("/delegation/status")
            
        assert response.status_code == 401
        assert "Authentication required" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_delegation_status_authenticated(self, mock_current_user, mock_auth_bypass, mock_blockchain_service):
        """Test delegation status check when authenticated."""
        # Setup mocks
        wallet_address = mock_current_user["walletAddress"]
        mock_blockchain_service.check_delegation.return_value = True
        
        app = self.setup_dependency_overrides(
            mock_blockchain_service=mock_blockchain_service,
            wallet_address=wallet_address
        )
        
        with mock_auth_bypass():
            with TestClient(app) as client:
                response = client.get("/delegation/status")
        
        self.cleanup_dependency_overrides()
        
        assert response.status_code == 200
        data = response.json()
        assert data["is_delegated"] is True
        assert data["server_wallet_address"] == settings.wallet_address
        assert data["user_wallet_address"] == wallet_address
        assert data["can_update_assets"] is True
        assert data["can_delete_assets"] is True

    @pytest.mark.asyncio
    async def test_delegation_status_not_delegated(self, mock_current_user, mock_auth_bypass, mock_blockchain_service):
        """Test delegation status when not delegated."""
        # Setup mocks
        wallet_address = mock_current_user["walletAddress"]
        mock_blockchain_service.check_delegation.return_value = False
        
        app = self.setup_dependency_overrides(
            mock_blockchain_service=mock_blockchain_service,
            wallet_address=wallet_address
        )
        
        with mock_auth_bypass():
            with TestClient(app) as client:
                response = client.get("/delegation/status")
        
        self.cleanup_dependency_overrides()
        
        assert response.status_code == 200
        data = response.json()
        assert data["is_delegated"] is False
        assert data["can_update_assets"] is False
        assert data["can_delete_assets"] is False

    @pytest.mark.asyncio
    async def test_set_delegation_requires_wallet_auth(self, mock_current_user):
        """Test that setting delegation requires wallet authentication."""
        from app.main import app
        
        # Mock API key authentication instead of wallet
        def mock_api_key_auth():
            mock_auth_context = {
                "wallet_address": mock_current_user["walletAddress"],
                "auth_method": "api_key",  # This should cause rejection
                "permissions": ["read", "write", "delete"]
            }
            return patch('app.utilities.auth_middleware.AuthManager.authenticate', 
                        new_callable=AsyncMock, return_value=mock_auth_context)
        
        app = self.setup_dependency_overrides(wallet_address=mock_current_user["walletAddress"])
        
        with mock_api_key_auth():
            with TestClient(app) as client:
                # Mock the request state for API key auth
                with patch('app.api.delegation_routes.Request') as mock_request:
                    mock_request.state.auth_context = {"auth_method": "api_key"}
                    response = client.post(
                        "/delegation/set",
                        json={
                            "delegate_address": settings.wallet_address,
                            "status": True
                        }
                    )
        
        self.cleanup_dependency_overrides()
        
        assert response.status_code == 403
        assert "wallet authentication" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_set_delegation_success(self, mock_current_user, mock_auth_bypass, mock_blockchain_service):
        """Test successful delegation transaction preparation."""
        # Setup mocks
        wallet_address = mock_current_user["walletAddress"]
        
        app = self.setup_dependency_overrides(
            mock_blockchain_service=mock_blockchain_service,
            wallet_address=wallet_address
        )
        
        with mock_auth_bypass():
            with TestClient(app) as client:
                # Mock the request state for wallet auth
                with patch('app.api.delegation_routes.Request') as mock_request:
                    mock_request.state.auth_context = {"auth_method": "wallet"}
                    response = client.post(
                        "/delegation/set",
                        json={
                            "delegate_address": settings.wallet_address,
                            "status": True
                        }
                    )
        
        self.cleanup_dependency_overrides()
        
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "transaction" in data
        assert data["action"] == "setDelegate"
        assert data["delegate_address"] == settings.wallet_address
        assert data["status"] is True

    @pytest.mark.asyncio
    async def test_set_delegation_invalid_delegate_address(self, mock_current_user, mock_auth_bypass, mock_blockchain_service):
        """Test delegation with invalid delegate address."""
        # Setup mocks
        wallet_address = mock_current_user["walletAddress"]
        invalid_address = "0x1234567890123456789012345678901234567890"  # Different from server wallet
        
        app = self.setup_dependency_overrides(
            mock_blockchain_service=mock_blockchain_service,
            wallet_address=wallet_address
        )
        
        with mock_auth_bypass():
            with TestClient(app) as client:
                # Mock the request state for wallet auth
                with patch('app.api.delegation_routes.Request') as mock_request:
                    mock_request.state.auth_context = {"auth_method": "wallet"}
                    response = client.post(
                        "/delegation/set",
                        json={
                            "delegate_address": invalid_address,
                            "status": True
                        }
                    )
        
        self.cleanup_dependency_overrides()
        
        assert response.status_code == 400
        assert "Invalid delegate address" in response.json()["detail"]
        assert settings.wallet_address in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_check_specific_delegation(self, mock_current_user, mock_auth_bypass, mock_blockchain_service):
        """Test checking specific delegation between two addresses."""
        # Setup mocks
        wallet_address = mock_current_user["walletAddress"]
        delegate_address = settings.wallet_address
        mock_blockchain_service.check_delegation.return_value = True
        
        app = self.setup_dependency_overrides(
            mock_blockchain_service=mock_blockchain_service,
            wallet_address=wallet_address
        )
        
        with mock_auth_bypass():
            with TestClient(app) as client:
                response = client.get(f"/delegation/check/{wallet_address}/{delegate_address}")
        
        self.cleanup_dependency_overrides()
        
        assert response.status_code == 200
        data = response.json()
        assert data["owner_address"] == wallet_address
        assert data["delegate_address"] == delegate_address
        assert data["is_delegated"] is True

    @pytest.mark.asyncio
    async def test_delegation_status_blockchain_error(self, mock_current_user, mock_auth_bypass, mock_blockchain_service):
        """Test delegation status when blockchain service throws error."""
        # Setup mocks
        wallet_address = mock_current_user["walletAddress"]
        mock_blockchain_service.check_delegation.side_effect = HTTPException(
            status_code=500,
            detail="Blockchain connection error"
        )
        
        app = self.setup_dependency_overrides(
            mock_blockchain_service=mock_blockchain_service,
            wallet_address=wallet_address
        )
        
        with mock_auth_bypass():
            with TestClient(app) as client:
                response = client.get("/delegation/status")
        
        self.cleanup_dependency_overrides()
        
        assert response.status_code == 500
        assert "Blockchain connection error" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_set_delegation_transaction_builder_failure(self, mock_current_user, mock_auth_bypass, mock_blockchain_service):
        """Test delegation when transaction builder fails."""
        # Setup mocks
        wallet_address = mock_current_user["walletAddress"]
        mock_blockchain_service.transaction_builder.build_set_delegate_transaction.return_value = {
            "success": False,
            "error": "Gas estimation failed"
        }
        
        app = self.setup_dependency_overrides(
            mock_blockchain_service=mock_blockchain_service,
            wallet_address=wallet_address
        )
        
        with mock_auth_bypass():
            with TestClient(app) as client:
                # Mock the request state for wallet auth
                with patch('app.api.delegation_routes.Request') as mock_request:
                    mock_request.state.auth_context = {"auth_method": "wallet"}
                    response = client.post(
                        "/delegation/set",
                        json={
                            "delegate_address": settings.wallet_address,
                            "status": True
                        }
                    )
        
        self.cleanup_dependency_overrides()
        
        assert response.status_code == 500
        assert "Gas estimation failed" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_revoke_delegation(self, mock_current_user, mock_auth_bypass, mock_blockchain_service):
        """Test revoking delegation."""
        # Setup mocks
        wallet_address = mock_current_user["walletAddress"]
        
        app = self.setup_dependency_overrides(
            mock_blockchain_service=mock_blockchain_service,
            wallet_address=wallet_address
        )
        
        with mock_auth_bypass():
            with TestClient(app) as client:
                # Mock the request state for wallet auth
                with patch('app.api.delegation_routes.Request') as mock_request:
                    mock_request.state.auth_context = {"auth_method": "wallet"}
                    response = client.post(
                        "/delegation/set",
                        json={
                            "delegate_address": settings.wallet_address,
                            "status": False  # Revoke delegation
                        }
                    )
        
        self.cleanup_dependency_overrides()
        
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["status"] is False  # Should be revoked
        assert data["action"] == "setDelegate"