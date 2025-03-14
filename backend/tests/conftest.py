# conftest.py
import pytest
import pytest_asyncio
from unittest.mock import MagicMock, AsyncMock
from datetime import datetime, timezone

# Fixed timestamp for use in tests for consistency
@pytest.fixture
def fixed_timestamp():
    """Return a fixed timestamp for testing."""
    return datetime(2025, 3, 13, 12, 0, 0, tzinfo=timezone.utc)

@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for each test case."""
    import asyncio
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()

# Database and Repository Mocks
@pytest.fixture
def mock_db_client():
    """Create mock database client with all required collections."""
    client = MagicMock()
    client.assets_collection = MagicMock()
    client.auth_collection = MagicMock()
    client.sessions_collection = MagicMock()
    client.transaction_collection = MagicMock()
    client.users_collection = MagicMock()
    return client

@pytest.fixture
def mock_asset_repo():
    """Create mock AssetRepository."""
    repo = MagicMock()
    repo.find_asset = AsyncMock()
    repo.find_assets = AsyncMock()
    repo.insert_asset = AsyncMock()
    repo.update_asset = AsyncMock()
    repo.update_assets = AsyncMock()
    repo.delete_asset = AsyncMock()
    return repo

@pytest.fixture
def mock_auth_repo():
    """Create mock AuthRepository."""
    repo = MagicMock()
    repo.get_auth_record = AsyncMock()
    repo.upsert_auth_record = AsyncMock()
    repo.insert_session = AsyncMock()
    repo.get_session = AsyncMock()
    repo.update_session = AsyncMock()
    repo.delete_session = AsyncMock()
    return repo

@pytest.fixture
def mock_transaction_repo():
    """Create mock TransactionRepository."""
    repo = MagicMock()
    repo.insert_transaction = AsyncMock()
    repo.find_transactions = AsyncMock()
    repo.find_transaction = AsyncMock()
    repo.update_transaction = AsyncMock()
    repo.delete_transaction = AsyncMock()
    return repo

@pytest.fixture
def mock_user_repo():
    """Create mock UserRepository."""
    repo = MagicMock()
    repo.insert_user = AsyncMock()
    repo.find_user = AsyncMock()
    repo.find_users = AsyncMock()
    repo.update_user = AsyncMock()
    repo.delete_user = AsyncMock()
    return repo

# Service Mocks
@pytest.fixture
def mock_asset_service():
    """Create mock AssetService."""
    service = MagicMock()
    service.get_asset = AsyncMock()
    service.get_asset_with_deleted = AsyncMock()
    service.get_documents_by_wallet = AsyncMock()
    service.create_asset = AsyncMock()
    service.create_new_version = AsyncMock()
    service.update_non_critical_metadata = AsyncMock()
    service.soft_delete = AsyncMock()
    service.undelete_asset = AsyncMock()
    service.get_version_history = AsyncMock()
    return service

@pytest.fixture
def mock_auth_service():
    """Create mock AuthService."""
    service = MagicMock()
    service.get_nonce = AsyncMock()
    service.generate_nonce = AsyncMock()
    service.verify_signature = AsyncMock()
    service.authenticate = AsyncMock()
    service.create_session = AsyncMock()
    service.validate_session = AsyncMock()
    service.logout = AsyncMock()
    service.extend_session = AsyncMock()
    return service

@pytest.fixture
def mock_transaction_service():
    """Create mock TransactionService."""
    service = MagicMock()
    service.get_asset_history = AsyncMock()
    service.get_wallet_history = AsyncMock()
    service.record_transaction = AsyncMock()
    service.get_transaction_by_id = AsyncMock()
    service.get_transaction_summary = AsyncMock()
    return service

@pytest.fixture
def mock_user_service():
    """Create mock UserService."""
    service = MagicMock()
    service.create_user = AsyncMock()
    service.get_user = AsyncMock()
    service.update_user = AsyncMock()
    service.update_last_login = AsyncMock()
    service.get_users_by_role = AsyncMock()
    service.delete_user = AsyncMock()
    return service

@pytest.fixture
def mock_blockchain_service():
    """Create mock BlockchainService."""
    service = MagicMock()
    service.store_hash = AsyncMock()
    service.get_hash_from_transaction = AsyncMock()
    service.get_cids_for_address = AsyncMock()
    service.verify_cid = AsyncMock()
    service.wallet_address = "0x9876543210987654321098765432109876543210"
    return service

@pytest.fixture
def mock_ipfs_service():
    """Create mock IPFSService."""
    service = MagicMock()
    service.store_metadata = AsyncMock()
    service.retrieve_metadata = AsyncMock()
    service.upload_files = AsyncMock()
    service.get_file_url = AsyncMock()
    service.get_file_contents = AsyncMock()
    service.compute_cid = AsyncMock()
    service.verify_cid = AsyncMock()
    return service

# Handler Mocks
@pytest.fixture
def mock_auth_handler():
    """Create mock AuthHandler."""
    handler = MagicMock()
    handler.get_nonce = AsyncMock()
    handler.authenticate = AsyncMock()
    handler.validate_session = AsyncMock()
    handler.logout = AsyncMock()
    return handler

@pytest.fixture
def mock_user_handler():
    """Create mock UserHandler."""
    handler = MagicMock()
    handler.register_user = AsyncMock()
    handler.get_user = AsyncMock()
    handler.update_user = AsyncMock()
    handler.delete_user = AsyncMock()
    handler.get_users_by_role = AsyncMock()
    return handler

@pytest.fixture
def mock_transaction_handler():
    """Create mock TransactionHandler."""
    handler = MagicMock()
    handler.get_asset_history = AsyncMock()
    handler.get_wallet_history = AsyncMock()
    handler.get_transaction_details = AsyncMock()
    handler.record_transaction = AsyncMock()
    handler.get_transaction_summary = AsyncMock()
    return handler

@pytest.fixture
def mock_upload_handler():
    """Create mock UploadHandler."""
    handler = MagicMock()
    handler.process_metadata = AsyncMock()
    handler.handle_metadata_upload = AsyncMock()
    handler.handle_json_files = AsyncMock()
    handler.process_csv_upload = AsyncMock()
    return handler

@pytest.fixture
def mock_retrieve_handler():
    """Create mock RetrieveHandler."""
    handler = MagicMock()
    handler.retrieve_metadata = AsyncMock()
    return handler

@pytest.fixture
def mock_delete_handler():
    """Create mock DeleteHandler."""
    handler = MagicMock()
    handler.delete_asset = AsyncMock()
    handler.undelete_asset = AsyncMock()
    handler.batch_delete_assets = AsyncMock()
    return handler

# Web Request/Response Mocks
@pytest.fixture
def mock_request():
    """Create mock FastAPI Request."""
    request = MagicMock()
    request.cookies = {}
    return request

@pytest.fixture
def mock_response():
    """Create mock FastAPI Response."""
    response = MagicMock()
    response.set_cookie = MagicMock()
    response.delete_cookie = MagicMock()
    return response

@pytest.fixture
def client():
    """Create test client for FastAPI app."""
    from fastapi.testclient import TestClient
    from app.main import app
    return TestClient(app)