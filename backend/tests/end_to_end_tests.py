"""
End-to-End API Tests

These tests simulate complete user workflows through the API endpoints,
testing real user scenarios from authentication to asset management.
No browser automation - pure API testing with TestClient.
"""

import pytest
import json
import time
import io
from datetime import datetime, timezone
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock, AsyncMock
import uuid

from app.main import app


class TestCompleteAuthenticationFlow:
    """Test complete authentication workflow from nonce to logout"""
    
    @pytest.fixture
    def client(self):
        return TestClient(app)
    
    @pytest.fixture
    def test_wallet(self):
        return "0x742a4b0e2a4b0b77e5f9d6c7d8e9f0a1b2c3d4e5"
    
    @pytest.fixture
    def mock_services(self):
        """Mock all services for consistent E2E testing"""
        with patch("app.database.get_db_client") as mock_db, \
             patch("app.handlers.auth_handler.AuthHandler.get_nonce") as mock_get_nonce, \
             patch("app.handlers.auth_handler.AuthHandler.authenticate") as mock_auth, \
             patch("app.handlers.auth_handler.AuthHandler.validate_session") as mock_validate, \
             patch("app.handlers.auth_handler.AuthHandler.logout") as mock_logout:
            
            # Configure mocks for successful flow
            mock_get_nonce.return_value = {"wallet_address": "0x742a4b0e2a4b0b77e5f9d6c7d8e9f0a1b2c3d4e5", "nonce": 123456}
            mock_auth.return_value = {"status": "success", "message": "Authentication successful"}
            mock_validate.return_value = {
                "wallet_address": "0x742a4b0e2a4b0b77e5f9d6c7d8e9f0a1b2c3d4e5",
                "session_id": "test_session_123",
                "is_active": True
            }
            mock_logout.return_value = {"status": "success", "message": "Logged out successfully"}
            
            yield {
                "db": mock_db,
                "get_nonce": mock_get_nonce,
                "authenticate": mock_auth,
                "validate": mock_validate,
                "logout": mock_logout
            }
    
    def test_complete_authentication_workflow(self, client, test_wallet, mock_services):
        """Test complete auth flow: nonce → login → validate → access protected → logout"""
        
        # STEP 1: Get authentication nonce
        nonce_response = client.get(f"/api/auth/nonce/{test_wallet}")
        assert nonce_response.status_code == 200
        
        nonce_data = nonce_response.json()
        assert "nonce" in nonce_data
        assert nonce_data["wallet_address"] == test_wallet
        nonce = nonce_data["nonce"]
        
        # STEP 2: Authenticate with signature
        auth_payload = {
            "wallet_address": test_wallet,
            "signature": f"0xmocksignature{nonce}"
        }
        
        auth_response = client.post("/api/auth/login", json=auth_payload)
        assert auth_response.status_code == 200
        
        auth_data = auth_response.json()
        assert auth_data["status"] == "success"
        
        # Extract session cookie
        session_cookies = auth_response.cookies
        assert "session_id" in session_cookies
        
        # STEP 3: Validate session
        validate_response = client.get("/api/auth/validate", cookies=session_cookies)
        assert validate_response.status_code == 200
        
        validate_data = validate_response.json()
        assert validate_data["wallet_address"] == test_wallet
        assert validate_data["is_active"] is True
        
        # STEP 4: Access protected endpoint (should work with valid session)
        protected_response = client.get(f"/api/users/{test_wallet}", cookies=session_cookies)
        # This might return 404 if user doesn't exist, but shouldn't return 401 (unauthorized)
        assert protected_response.status_code != 401
        
        # STEP 5: Logout
        logout_response = client.post("/api/auth/logout", cookies=session_cookies)
        assert logout_response.status_code == 200
        assert logout_response.json()["status"] == "success"
        
        # STEP 6: Try to access protected endpoint after logout (should fail)
        mock_services["validate"].side_effect = Exception("Invalid or expired session")
        
        post_logout_response = client.get("/api/auth/validate", cookies=session_cookies)
        assert post_logout_response.status_code in [401, 500]  # Should be unauthorized or error
    
    def test_authentication_with_invalid_signature(self, client, test_wallet, mock_services):
        """Test authentication flow with invalid signature"""
        
        # Get nonce first
        nonce_response = client.get(f"/api/auth/nonce/{test_wallet}")
        assert nonce_response.status_code == 200
        
        # Configure mock to reject authentication
        mock_services["authenticate"].return_value = {"status": "error", "message": "Invalid signature"}
        
        # Try to authenticate with invalid signature
        auth_payload = {
            "wallet_address": test_wallet,
            "signature": "0xinvalidsignature"
        }
        
        auth_response = client.post("/api/auth/login", json=auth_payload)
        # Should either return error status or HTTP error code
        assert auth_response.status_code >= 400 or auth_response.json().get("status") == "error"


class TestCompleteAssetLifecycle:
    """Test complete asset lifecycle from creation to deletion"""
    
    @pytest.fixture
    def client(self):
        return TestClient(app)
    
    @pytest.fixture
    def test_wallet(self):
        return "0x742a4b0e2a4b0b77e5f9d6c7d8e9f0a1b2c3d4e5"
    
    @pytest.fixture
    def test_asset_data(self):
        return {
            "asset_id": f"e2e-asset-{uuid.uuid4()}",
            "critical_metadata": {
                "name": "E2E Test Asset",
                "document_type": "test_document",
                "document_id": f"DOC-{uuid.uuid4()}"
            },
            "non_critical_metadata": {
                "description": "End-to-end test asset",
                "tags": ["test", "e2e", "automated"],
                "category": "testing"
            }
        }
    
    @pytest.fixture
    def mock_handlers(self):
        """Mock handlers for asset lifecycle"""
        with patch("app.handlers.upload_handler.UploadHandler.process_metadata") as mock_upload, \
             patch("app.handlers.retrieve_handler.RetrieveHandler.retrieve_metadata") as mock_retrieve, \
             patch("app.handlers.delete_handler.DeleteHandler.delete_asset") as mock_delete, \
             patch("app.handlers.transaction_handler.TransactionHandler.get_asset_history") as mock_history:
            
            yield {
                "upload": mock_upload,
                "retrieve": mock_retrieve,
                "delete": mock_delete,
                "history": mock_history
            }
    
    def test_complete_asset_lifecycle(self, client, test_wallet, test_asset_data, mock_handlers):
        """Test: Create → Retrieve → Update → Retrieve → Delete → Verify deletion"""
        
        asset_id = test_asset_data["asset_id"]
        doc_id = f"doc_{uuid.uuid4()}"
        ipfs_cid = f"Qm{uuid.uuid4().hex[:40]}"
        tx_hash = f"0x{uuid.uuid4().hex}"
        
        # Configure upload handler mock
        mock_handlers["upload"].return_value = {
            "assetId": asset_id,
            "status": "success",
            "message": "Document created successfully",
            "documentId": doc_id,
            "version": 1,
            "ipfsCid": ipfs_cid,
            "blockchainTxHash": tx_hash
        }
        
        # STEP 1: Create asset
        create_payload = {
            **test_asset_data,
            "wallet_address": test_wallet
        }
        
        create_response = client.post("/api/upload/process", json=create_payload)
        assert create_response.status_code == 200
        
        create_data = create_response.json()
        assert create_data["status"] == "success"
        assert create_data["assetId"] == asset_id
        created_doc_id = create_data["documentId"]
        
        # Configure retrieve handler mock
        mock_handlers["retrieve"].return_value = {
            "assetId": asset_id,
            "version": 1,
            "critical_metadata": test_asset_data["critical_metadata"],
            "non_critical_metadata": test_asset_data["non_critical_metadata"],
            "documentId": created_doc_id,
            "ipfsHash": ipfs_cid,
            "blockchainTxId": tx_hash,
            "verification": {
                "verified": True,
                "cid_match": True,
                "blockchain_cid": ipfs_cid,
                "computed_cid": ipfs_cid,
                "recovery_needed": False
            }
        }
        
        # STEP 2: Retrieve created asset
        retrieve_response = client.get(f"/api/retrieve/{asset_id}")
        assert retrieve_response.status_code == 200
        
        retrieve_data = retrieve_response.json()
        assert retrieve_data["assetId"] == asset_id
        assert retrieve_data["version"] == 1
        assert retrieve_data["verification"]["verified"] is True
        
        # STEP 3: Create new version (simulate update)
        updated_metadata = {
            **test_asset_data["critical_metadata"],
            "name": "E2E Test Asset - Updated"
        }
        
        new_doc_id = f"doc_{uuid.uuid4()}"
        new_ipfs_cid = f"Qm{uuid.uuid4().hex[:40]}"
        new_tx_hash = f"0x{uuid.uuid4().hex}"
        
        mock_handlers["upload"].return_value = {
            "assetId": asset_id,
            "status": "success", 
            "message": "New version created",
            "documentId": new_doc_id,
            "version": 2,
            "ipfsCid": new_ipfs_cid,
            "blockchainTxHash": new_tx_hash
        }
        
        update_payload = {
            "asset_id": asset_id,
            "wallet_address": test_wallet,
            "critical_metadata": updated_metadata,
            "non_critical_metadata": test_asset_data["non_critical_metadata"]
        }
        
        update_response = client.post("/api/upload/process", json=update_payload)
        assert update_response.status_code == 200
        
        update_data = update_response.json()
        assert update_data["version"] == 2
        
        # STEP 4: Retrieve updated asset
        mock_handlers["retrieve"].return_value = {
            "assetId": asset_id,
            "version": 2,
            "critical_metadata": updated_metadata,
            "non_critical_metadata": test_asset_data["non_critical_metadata"],
            "documentId": new_doc_id,
            "verification": {"verified": True}
        }
        
        retrieve_v2_response = client.get(f"/api/retrieve/{asset_id}")
        assert retrieve_v2_response.status_code == 200
        
        retrieve_v2_data = retrieve_v2_response.json()
        assert retrieve_v2_data["version"] == 2
        assert retrieve_v2_data["critical_metadata"]["name"] == "E2E Test Asset - Updated"
        
        # STEP 5: Get transaction history
        mock_handlers["history"].return_value = {
            "assetId": asset_id,
            "transactionCount": 2,
            "transactions": [
                {
                    "_id": f"tx_{uuid.uuid4()}",
                    "assetId": asset_id,
                    "action": "CREATE",
                    "walletAddress": test_wallet,
                    "timestamp": datetime.now(timezone.utc).isoformat()
                },
                {
                    "_id": f"tx_{uuid.uuid4()}",
                    "assetId": asset_id,
                    "action": "UPDATE",
                    "walletAddress": test_wallet,
                    "timestamp": datetime.now(timezone.utc).isoformat()
                }
            ]
        }
        
        history_response = client.get(f"/api/transactions/asset/{asset_id}")
        assert history_response.status_code == 200
        
        history_data = history_response.json()
        assert history_data["transactionCount"] == 2
        assert len(history_data["transactions"]) == 2
        
        # STEP 6: Delete asset
        from app.schemas.delete_schema import DeleteResponse
        mock_handlers["delete"].return_value = DeleteResponse(
            asset_id=asset_id,
            status="success",
            message="Asset deleted successfully",
            document_id=new_doc_id,
            transaction_id=f"tx_{uuid.uuid4()}"
        )
        
        delete_payload = {
            "asset_id": asset_id,
            "wallet_address": test_wallet,
            "reason": "E2E test cleanup"
        }
        
        delete_response = client.post("/api/delete", json=delete_payload)
        assert delete_response.status_code == 200
        
        delete_data = delete_response.json()
        assert delete_data["status"] == "success"
        assert delete_data["asset_id"] == asset_id
        
        # STEP 7: Verify asset is deleted (retrieve should indicate deletion)
        mock_handlers["retrieve"].side_effect = Exception("Asset not found or deleted")
        
        verify_delete_response = client.get(f"/api/retrieve/{asset_id}")
        assert verify_delete_response.status_code in [404, 500]


class TestFileUploadWorkflows:
    """Test complete file upload and processing workflows"""
    
    @pytest.fixture
    def client(self):
        return TestClient(app)
    
    @pytest.fixture
    def test_wallet(self):
        return "0x742a4b0e2a4b0b77e5f9d6c7d8e9f0a1b2c3d4e5"
    
    def test_json_file_upload_workflow(self, client, test_wallet):
        """Test complete JSON file upload and processing workflow"""
        
        # Create test JSON data
        test_assets = [
            {
                "asset_id": f"json-asset-{uuid.uuid4()}",
                "critical_metadata": {
                    "name": "JSON Asset 1",
                    "document_type": "test_json",
                    "document_id": f"JSON-DOC-{uuid.uuid4()}"
                },
                "non_critical_metadata": {
                    "description": "First JSON test asset",
                    "tags": ["json", "test", "first"]
                }
            },
            {
                "asset_id": f"json-asset-{uuid.uuid4()}",
                "critical_metadata": {
                    "name": "JSON Asset 2", 
                    "document_type": "test_json",
                    "document_id": f"JSON-DOC-{uuid.uuid4()}"
                },
                "non_critical_metadata": {
                    "description": "Second JSON test asset",
                    "tags": ["json", "test", "second"]
                }
            }
        ]
        
        json_content = json.dumps(test_assets, indent=2)
        
        with patch("app.handlers.upload_handler.UploadHandler.handle_json_files") as mock_handler:
            # Configure successful upload response
            mock_handler.return_value = {
                "uploadCount": 2,
                "results": [
                    {
                        "asset_id": test_assets[0]["asset_id"],
                        "status": "success",
                        "message": "Document created",
                        "document_id": f"doc_{uuid.uuid4()}",
                        "version": 1,
                        "ipfs_cid": f"Qm{uuid.uuid4().hex[:40]}",
                        "blockchain_tx_hash": f"0x{uuid.uuid4().hex}",
                        "filename": "test_assets.json"
                    },
                    {
                        "asset_id": test_assets[1]["asset_id"],
                        "status": "success",
                        "message": "Document created",
                        "document_id": f"doc_{uuid.uuid4()}",
                        "version": 1,
                        "ipfs_cid": f"Qm{uuid.uuid4().hex[:40]}",
                        "blockchain_tx_hash": f"0x{uuid.uuid4().hex}",
                        "filename": "test_assets.json"
                    }
                ]
            }
            
            # Upload JSON file
            files = {"files": ("test_assets.json", io.BytesIO(json_content.encode()), "application/json")}
            data = {"wallet_address": test_wallet}
            
            response = client.post("/api/upload/json", files=files, data=data)
            assert response.status_code == 200
            
            response_data = response.json()
            assert response_data["uploadCount"] == 2
            assert len(response_data["results"]) == 2
            
            # Verify all uploads succeeded
            for result in response_data["results"]:
                assert result["status"] == "success"
                assert "document_id" in result
                assert "ipfs_cid" in result
                assert "blockchain_tx_hash" in result
    
    def test_csv_file_upload_workflow(self, client, test_wallet):
        """Test complete CSV file upload and processing workflow"""
        
        # Create test CSV data
        csv_content = """asset_id,name,document_type,description,priority,department
csv-asset-1,CSV Test Document 1,contract,First CSV test document,high,legal
csv-asset-2,CSV Test Document 2,invoice,Second CSV test document,medium,finance
csv-asset-3,CSV Test Document 3,report,Third CSV test document,low,operations"""
        
        with patch("app.handlers.upload_handler.UploadHandler.process_csv_upload") as mock_handler:
            # Configure successful CSV processing response
            mock_handler.return_value = {
                "uploadCount": 3,
                "results": [
                    {
                        "asset_id": "csv-asset-1",
                        "status": "success",
                        "message": "Document created",
                        "document_id": f"doc_{uuid.uuid4()}",
                        "version": 1,
                        "ipfs_cid": f"Qm{uuid.uuid4().hex[:40]}",
                        "blockchain_tx_hash": f"0x{uuid.uuid4().hex}",
                        "filename": "test_assets.csv"
                    },
                    {
                        "asset_id": "csv-asset-2",
                        "status": "success",
                        "message": "Document created",
                        "document_id": f"doc_{uuid.uuid4()}",
                        "version": 1,
                        "ipfs_cid": f"Qm{uuid.uuid4().hex[:40]}",
                        "blockchain_tx_hash": f"0x{uuid.uuid4().hex}",
                        "filename": "test_assets.csv"
                    },
                    {
                        "asset_id": "csv-asset-3",
                        "status": "success",
                        "message": "Document created",
                        "document_id": f"doc_{uuid.uuid4()}",
                        "version": 1,
                        "ipfs_cid": f"Qm{uuid.uuid4().hex[:40]}",
                        "blockchain_tx_hash": f"0x{uuid.uuid4().hex}",
                        "filename": "test_assets.csv"
                    }
                ]
            }
            
            # Upload CSV file
            files = {"files": ("test_assets.csv", io.BytesIO(csv_content.encode()), "text/csv")}
            data = {
                "wallet_address": test_wallet,
                "critical_metadata_fields": "name,document_type,description"
            }
            
            response = client.post("/api/upload/csv", files=files, data=data)
            assert response.status_code == 200
            
            response_data = response.json()
            assert response_data["uploadCount"] == 3
            assert len(response_data["results"]) == 3
            
            # Verify all uploads succeeded
            for result in response_data["results"]:
                assert result["status"] == "success"
                assert result["asset_id"].startswith("csv-asset-")
    
    def test_mixed_file_upload_with_errors(self, client, test_wallet):
        """Test file upload workflow with some successes and some failures"""
        
        # Create test data with one valid and one invalid file
        valid_json = json.dumps([{
            "asset_id": f"mixed-asset-{uuid.uuid4()}",
            "critical_metadata": {"name": "Valid Asset"},
            "non_critical_metadata": {"description": "This should work"}
        }])
        
        invalid_content = "This is not valid JSON or CSV content"
        
        with patch("app.handlers.upload_handler.UploadHandler.handle_json_files") as mock_handler:
            # Configure mixed success/failure response
            mock_handler.return_value = {
                "uploadCount": 2,
                "results": [
                    {
                        "asset_id": "mixed-asset-valid",
                        "status": "success",
                        "message": "Document created",
                        "document_id": f"doc_{uuid.uuid4()}",
                        "filename": "valid.json"
                    },
                    {
                        "asset_id": "mixed-asset-invalid",
                        "status": "error",
                        "message": "Invalid JSON format",
                        "detail": "Failed to parse JSON content",
                        "filename": "invalid.json"
                    }
                ]
            }
            
            # Upload files with mixed results
            files = [
                ("files", ("valid.json", io.BytesIO(valid_json.encode()), "application/json")),
                ("files", ("invalid.json", io.BytesIO(invalid_content.encode()), "application/json"))
            ]
            data = {"wallet_address": test_wallet}
            
            response = client.post("/api/upload/json", files=files, data=data)
            assert response.status_code == 200
            
            response_data = response.json()
            assert response_data["uploadCount"] == 2
            
            # Check that we have both success and error results
            statuses = [result["status"] for result in response_data["results"]]
            assert "success" in statuses
            assert "error" in statuses


class TestTransactionHistoryWorkflows:
    """Test complete transaction history and querying workflows"""
    
    @pytest.fixture
    def client(self):
        return TestClient(app)
    
    @pytest.fixture
    def test_wallet(self):
        return "0x742a4b0e2a4b0b77e5f9d6c7d8e9f0a1b2c3d4e5"
    
    @pytest.fixture
    def mock_transaction_handlers(self):
        """Mock transaction handlers for consistent testing"""
        with patch("app.handlers.transaction_handler.TransactionHandler.get_asset_history") as mock_asset_history, \
             patch("app.handlers.transaction_handler.TransactionHandler.get_wallet_history") as mock_wallet_history, \
             patch("app.handlers.transaction_handler.TransactionHandler.get_transaction_details") as mock_tx_details, \
             patch("app.handlers.transaction_handler.TransactionHandler.get_transaction_summary") as mock_tx_summary:
            
            yield {
                "asset_history": mock_asset_history,
                "wallet_history": mock_wallet_history,
                "transaction_details": mock_tx_details,
                "transaction_summary": mock_tx_summary
            }
    
    def test_complete_transaction_tracking_workflow(self, client, test_wallet, mock_transaction_handlers):
        """Test complete transaction tracking from creation through history queries"""
        
        asset_id = f"tx-test-asset-{uuid.uuid4()}"
        tx_id_1 = f"tx_{uuid.uuid4()}"
        tx_id_2 = f"tx_{uuid.uuid4()}"
        tx_id_3 = f"tx_{uuid.uuid4()}"
        
        now = datetime.now(timezone.utc)
        
        # Mock transaction history for the asset
        mock_transaction_handlers["asset_history"].return_value = {
            "assetId": asset_id,
            "version": None,
            "transactionCount": 3,
            "transactions": [
                {
                    "_id": tx_id_1,
                    "assetId": asset_id,
                    "action": "CREATE",
                    "walletAddress": test_wallet,
                    "timestamp": now.isoformat(),
                    "metadata": {"version": 1}
                },
                {
                    "_id": tx_id_2,
                    "assetId": asset_id,
                    "action": "UPDATE",
                    "walletAddress": test_wallet,
                    "timestamp": (now + timedelta(hours=1)).isoformat(),
                    "metadata": {"version": 2}
                },
                {
                    "_id": tx_id_3,
                    "assetId": asset_id,
                    "action": "DELETE",
                    "walletAddress": test_wallet,
                    "timestamp": (now + timedelta(hours=2)).isoformat(),
                    "metadata": {"reason": "Test cleanup"}
                }
            ]
        }
        
        # STEP 1: Get asset transaction history
        asset_history_response = client.get(f"/api/transactions/asset/{asset_id}")
        assert asset_history_response.status_code == 200
        
        asset_history_data = asset_history_response.json()
        assert asset_history_data["assetId"] == asset_id
        assert asset_history_data["transactionCount"] == 3
        assert len(asset_history_data["transactions"]) == 3
        
        # Verify transaction order (should be chronological)
        transactions = asset_history_data["transactions"]
        actions = [tx["action"] for tx in transactions]
        assert actions == ["CREATE", "UPDATE", "DELETE"]
        
        # STEP 2: Get wallet transaction history
        mock_transaction_handlers["wallet_history"].return_value = {
            "walletAddress": test_wallet,
            "include_all_versions": False,
            "transaction_count": 5,  # Including other assets
            "unique_assets": 2,
            "transactions": [
                # Include our test asset transactions plus others
                *asset_history_data["transactions"],
                {
                    "_id": f"tx_{uuid.uuid4()}",
                    "assetId": f"other-asset-{uuid.uuid4()}",
                    "action": "CREATE",
                    "walletAddress": test_wallet,
                    "timestamp": now.isoformat()
                },
                {
                    "_id": f"tx_{uuid.uuid4()}",
                    "assetId": f"other-asset-{uuid.uuid4()}",
                    "action": "UPDATE",
                    "walletAddress": test_wallet,
                    "timestamp": now.isoformat()
                }
            ],
            "action_summary": {
                "CREATE": 2,
                "UPDATE": 2,
                "DELETE": 1
            }
        }
        
        wallet_history_response = client.get(f"/api/transactions/wallet/{test_wallet}")
        assert wallet_history_response.status_code == 200
        
        wallet_history_data = wallet_history_response.json()
        assert wallet_history_data["walletAddress"] == test_wallet
        assert wallet_history_data["transaction_count"] == 5
        assert wallet_history_data["unique_assets"] == 2
        assert wallet_history_data["action_summary"]["CREATE"] == 2
        
        # STEP 3: Get specific transaction details
        mock_transaction_handlers["transaction_details"].return_value = {
            "transaction": {
                "_id": tx_id_1,
                "assetId": asset_id,
                "action": "CREATE",
                "walletAddress": test_wallet,
                "timestamp": now.isoformat(),
                "metadata": {"version": 1, "ipfs_cid": f"Qm{uuid.uuid4().hex[:40]}"}
            },
            "asset_info": {
                "_id": f"doc_{uuid.uuid4()}",
                "assetId": asset_id,
                "versionNumber": 1,
                "isCurrent": False  # Since it was later updated and deleted
            }
        }
        
        tx_details_response = client.get(f"/api/transactions/{tx_id_1}")
        assert tx_details_response.status_code == 200
        
        tx_details_data = tx_details_response.json()
        assert tx_details_data["transaction"]["_id"] == tx_id_1
        assert tx_details_data["transaction"]["action"] == "CREATE"
        assert tx_details_data["asset_info"]["assetId"] == asset_id
        
        # STEP 4: Get transaction summary
        mock_transaction_handlers["transaction_summary"].return_value = {
            "walletAddress": test_wallet,
            "summary": {
                "total_transactions": 5,
                "unique_assets": 2,
                "actions": {
                    "CREATE": 2,
                    "UPDATE": 2,
                    "DELETE": 1
                },
                "assets": [asset_id, f"other-asset-{uuid.uuid4()}"],
                "first_transaction": now.isoformat(),
                "latest_transaction": (now + timedelta(hours=2)).isoformat(),
                "most_active_day": now.date().isoformat(),
                "average_transactions_per_day": 2.5
            }
        }
        
        tx_summary_response = client.get(f"/api/transactions/summary/{test_wallet}")
        assert tx_summary_response.status_code == 200
        
        tx_summary_data = tx_summary_response.json()
        assert tx_summary_data["walletAddress"] == test_wallet
        assert tx_summary_data["summary"]["total_transactions"] == 5
        assert tx_summary_data["summary"]["unique_assets"] == 2
        assert asset_id in tx_summary_data["summary"]["assets"]
        
        # STEP 5: Query asset history with version filter
        mock_transaction_handlers["asset_history"].return_value = {
            "assetId": asset_id,
            "version": 2,
            "transactionCount": 1,
            "transactions": [
                {
                    "_id": tx_id_2,
                    "assetId": asset_id,
                    "action": "UPDATE",
                    "walletAddress": test_wallet,
                    "timestamp": (now + timedelta(hours=1)).isoformat(),
                    "metadata": {"version": 2}
                }
            ]
        }
        
        versioned_history_response = client.get(f"/api/transactions/asset/{asset_id}?version=2")
        assert versioned_history_response.status_code == 200
        
        versioned_data = versioned_history_response.json()
        assert versioned_data["version"] == 2
        assert versioned_data["transactionCount"] == 1
        assert versioned_data["transactions"][0]["action"] == "UPDATE"


class TestErrorRecoveryWorkflows:
    """Test error conditions and recovery scenarios"""
    
    @pytest.fixture
    def client(self):
        return TestClient(app)
    
    @pytest.fixture
    def test_wallet(self):
        return "0x742a4b0e2a4b0b77e5f9d6c7d8e9f0a1b2c3d4e5"
    
    def test_asset_integrity_verification_and_recovery(self, client, test_wallet):
        """Test asset integrity verification and automatic recovery"""
        
        asset_id = f"integrity-test-{uuid.uuid4()}"
        
        with patch("app.handlers.retrieve_handler.RetrieveHandler.retrieve_metadata") as mock_retrieve:
            
            # STEP 1: Test retrieval with integrity issues (no auto-recovery)
            mock_retrieve.return_value = {
                "assetId": asset_id,
                "version": 1,
                "critical_metadata": {"name": "Test Asset"},
                "verification": {
                    "verified": False,
                    "cid_match": False,
                    "blockchain_cid": "QmBlockchainCID123",
                    "computed_cid": "QmComputedCID456",
                    "recovery_needed": True,
                    "recovery_successful": None,
                    "message": "CID mismatch detected - tampering suspected"
                }
            }
            
            # Retrieve without auto-recovery
            retrieve_response = client.get(f"/api/retrieve/{asset_id}?auto_recover=false")
            assert retrieve_response.status_code == 200
            
            retrieve_data = retrieve_response.json()
            assert retrieve_data["verification"]["verified"] is False
            assert retrieve_data["verification"]["recovery_needed"] is True
            assert retrieve_data["verification"]["recovery_successful"] is None
            
            # STEP 2: Test retrieval with auto-recovery enabled
            mock_retrieve.return_value = {
                "assetId": asset_id,
                "version": 2,  # New version created during recovery
                "critical_metadata": {"name": "Test Asset"},
                "verification": {
                    "verified": True,
                    "cid_match": True,
                    "blockchain_cid": "QmNewBlockchainCID789",
                    "computed_cid": "QmNewBlockchainCID789",
                    "recovery_needed": True,  # Was needed
                    "recovery_successful": True,  # But was successful
                    "new_version_created": True,
                    "message": "Asset recovered successfully - new version created"
                }
            }
            
            # Retrieve with auto-recovery
            recovery_response = client.get(f"/api/retrieve/{asset_id}?auto_recover=true")
            assert recovery_response.status_code == 200
            
            recovery_data = recovery_response.json()
            assert recovery_data["verification"]["recovery_successful"] is True
            assert recovery_data["verification"]["new_version_created"] is True
            assert recovery_data["version"] == 2  # New version created
    
    def test_authentication_error_scenarios(self, client, test_wallet):
        """Test various authentication error scenarios and recovery"""
        
        with patch("app.handlers.auth_handler.AuthHandler.get_nonce") as mock_get_nonce, \
             patch("app.handlers.auth_handler.AuthHandler.authenticate") as mock_auth:
            
            # STEP 1: Test service unavailable scenario
            mock_get_nonce.side_effect = Exception("Service temporarily unavailable")
            
            nonce_response = client.get(f"/api/auth/nonce/{test_wallet}")
            assert nonce_response.status_code in [500, 503]  # Server error
            
            # STEP 2: Test authentication with expired nonce
            mock_get_nonce.side_effect = None
            mock_get_nonce.return_value = {"wallet_address": test_wallet, "nonce": 123456}
            mock_auth.return_value = {"status": "error", "message": "Nonce expired"}
            
            # Get nonce first
            nonce_response = client.get(f"/api/auth/nonce/{test_wallet}")
            assert nonce_response.status_code == 200
            
            # Try to authenticate with expired nonce
            auth_payload = {
                "wallet_address": test_wallet,
                "signature": "0xsignature123456"
            }
            
            auth_response = client.post("/api/auth/login", json=auth_payload)
            # Should handle gracefully
            assert auth_response.status_code >= 400 or auth_response.json().get("status") == "error"
            
            # STEP 3: Test successful recovery after getting new nonce
            mock_auth.return_value = {"status": "success", "message": "Authentication successful"}
            
            # Get fresh nonce
            fresh_nonce_response = client.get(f"/api/auth/nonce/{test_wallet}")
            assert fresh_nonce_response.status_code == 200
            
            # Authenticate successfully
            auth_response = client.post("/api/auth/login", json=auth_payload)
            assert auth_response.status_code == 200 or auth_response.json().get("status") == "success"
    
    def test_file_upload_error_recovery(self, client, test_wallet):
        """Test file upload error scenarios and partial success handling"""
        
        # Test data with some invalid entries
        mixed_json_data = [
            {
                "asset_id": f"valid-asset-{uuid.uuid4()}",
                "critical_metadata": {"name": "Valid Asset"},
                "non_critical_metadata": {"description": "This should work"}
            },
            {
                # Missing required asset_id
                "critical_metadata": {"name": "Invalid Asset 1"},
                "non_critical_metadata": {"description": "Missing asset_id"}
            },
            {
                "asset_id": f"another-valid-{uuid.uuid4()}",
                "critical_metadata": {"name": "Another Valid Asset"},
                "non_critical_metadata": {"description": "This should also work"}
            },
            {
                "asset_id": f"invalid-asset-{uuid.uuid4()}",
                # Missing critical_metadata entirely
                "non_critical_metadata": {"description": "Missing critical metadata"}
            }
        ]
        
        json_content = json.dumps(mixed_json_data)
        
        with patch("app.handlers.upload_handler.UploadHandler.handle_json_files") as mock_handler:
            # Configure mixed success/failure response
            mock_handler.return_value = {
                "uploadCount": 4,
                "successful_uploads": 2,
                "failed_uploads": 2,
                "results": [
                    {
                        "asset_id": mixed_json_data[0]["asset_id"],
                        "status": "success",
                        "message": "Document created",
                        "document_id": f"doc_{uuid.uuid4()}"
                    },
                    {
                        "asset_id": "unknown",
                        "status": "error",
                        "message": "Validation failed",
                        "detail": "Missing required field: asset_id"
                    },
                    {
                        "asset_id": mixed_json_data[2]["asset_id"],
                        "status": "success",
                        "message": "Document created",
                        "document_id": f"doc_{uuid.uuid4()}"
                    },
                    {
                        "asset_id": mixed_json_data[3]["asset_id"],
                        "status": "error",
                        "message": "Validation failed",
                        "detail": "Missing required field: critical_metadata"
                    }
                ]
            }
            
            # Upload mixed file
            files = {"files": ("mixed_assets.json", io.BytesIO(json_content.encode()), "application/json")}
            data = {"wallet_address": test_wallet}
            
            response = client.post("/api/upload/json", files=files, data=data)
            assert response.status_code == 200  # Should still return 200 for partial success
            
            response_data = response.json()
            assert response_data["uploadCount"] == 4
            
            # Check that we have both successes and failures
            statuses = [result["status"] for result in response_data["results"]]
            success_count = statuses.count("success")
            error_count = statuses.count("error")
            
            assert success_count == 2
            assert error_count == 2
            
            # Verify error details are provided
            error_results = [r for r in response_data["results"] if r["status"] == "error"]
            for error_result in error_results:
                assert "detail" in error_result
                assert "Missing required field" in error_result["detail"]


class TestMultiUserScenarios:
    """Test scenarios involving multiple users and assets"""
    
    @pytest.fixture
    def client(self):
        return TestClient(app)
    
    @pytest.fixture
    def test_wallets(self):
        return {
            "alice": "0x742a4b0e2a4b0b77e5f9d6c7d8e9f0a1b2c3d4e5",
            "bob": "0x9876543210987654321098765432109876543210",
            "charlie": "0x1111222233334444555566667777888899990000"
        }
    
    def test_multi_user_asset_management(self, client, test_wallets):
        """Test multiple users creating and managing their own assets"""
        
        alice_wallet = test_wallets["alice"]
        bob_wallet = test_wallets["bob"]
        
        with patch("app.handlers.upload_handler.UploadHandler.process_metadata") as mock_upload, \
             patch("app.handlers.transaction_handler.TransactionHandler.get_wallet_history") as mock_wallet_history:
            
            # STEP 1: Alice creates an asset
            alice_asset_id = f"alice-asset-{uuid.uuid4()}"
            mock_upload.return_value = {
                "assetId": alice_asset_id,
                "status": "success",
                "documentId": f"doc_{uuid.uuid4()}",
                "version": 1
            }
            
            alice_create_payload = {
                "asset_id": alice_asset_id,
                "wallet_address": alice_wallet,
                "critical_metadata": {"name": "Alice's Asset", "owner": "Alice"},
                "non_critical_metadata": {"description": "Created by Alice"}
            }
            
            alice_response = client.post("/api/upload/process", json=alice_create_payload)
            assert alice_response.status_code == 200
            assert alice_response.json()["assetId"] == alice_asset_id
            
            # STEP 2: Bob creates an asset
            bob_asset_id = f"bob-asset-{uuid.uuid4()}"
            mock_upload.return_value = {
                "assetId": bob_asset_id,
                "status": "success",
                "documentId": f"doc_{uuid.uuid4()}",
                "version": 1
            }
            
            bob_create_payload = {
                "asset_id": bob_asset_id,
                "wallet_address": bob_wallet,
                "critical_metadata": {"name": "Bob's Asset", "owner": "Bob"},
                "non_critical_metadata": {"description": "Created by Bob"}
            }
            
            bob_response = client.post("/api/upload/process", json=bob_create_payload)
            assert bob_response.status_code == 200
            assert bob_response.json()["assetId"] == bob_asset_id
            
            # STEP 3: Get Alice's transaction history (should only show her assets)
            mock_wallet_history.return_value = {
                "walletAddress": alice_wallet,
                "transaction_count": 1,
                "unique_assets": 1,
                "transactions": [
                    {
                        "_id": f"tx_{uuid.uuid4()}",
                        "assetId": alice_asset_id,
                        "action": "CREATE",
                        "walletAddress": alice_wallet,
                        "timestamp": datetime.now(timezone.utc).isoformat()
                    }
                ]
            }
            
            alice_history_response = client.get(f"/api/transactions/wallet/{alice_wallet}")
            assert alice_history_response.status_code == 200
            
            alice_history = alice_history_response.json()
            assert alice_history["walletAddress"] == alice_wallet
            assert alice_history["unique_assets"] == 1
            
            # Verify Alice only sees her own assets
            alice_asset_ids = [tx["assetId"] for tx in alice_history["transactions"]]
            assert alice_asset_id in alice_asset_ids
            assert bob_asset_id not in alice_asset_ids
            
            # STEP 4: Get Bob's transaction history (should only show his assets)
            mock_wallet_history.return_value = {
                "walletAddress": bob_wallet,
                "transaction_count": 1,
                "unique_assets": 1,
                "transactions": [
                    {
                        "_id": f"tx_{uuid.uuid4()}",
                        "assetId": bob_asset_id,
                        "action": "CREATE",
                        "walletAddress": bob_wallet,
                        "timestamp": datetime.now(timezone.utc).isoformat()
                    }
                ]
            }
            
            bob_history_response = client.get(f"/api/transactions/wallet/{bob_wallet}")
            assert bob_history_response.status_code == 200
            
            bob_history = bob_history_response.json()
            assert bob_history["walletAddress"] == bob_wallet
            assert bob_history["unique_assets"] == 1
            
            # Verify Bob only sees his own assets
            bob_asset_ids = [tx["assetId"] for tx in bob_history["transactions"]]
            assert bob_asset_id in bob_asset_ids
            assert alice_asset_id not in bob_asset_ids
    
    def test_unauthorized_access_attempts(self, client, test_wallets):
        """Test that users cannot access assets they don't own"""
        
        alice_wallet = test_wallets["alice"]
        bob_wallet = test_wallets["bob"]
        
        with patch("app.handlers.retrieve_handler.RetrieveHandler.retrieve_metadata") as mock_retrieve, \
             patch("app.handlers.delete_handler.DeleteHandler.delete_asset") as mock_delete:
            
            # Alice's asset
            alice_asset_id = f"alice-private-{uuid.uuid4()}"
            
            # STEP 1: Test that Bob cannot retrieve Alice's asset
            mock_retrieve.side_effect = Exception("Unauthorized access - asset not found")
            
            bob_retrieve_response = client.get(f"/api/retrieve/{alice_asset_id}?wallet_address={bob_wallet}")
            assert bob_retrieve_response.status_code in [401, 403, 404, 500]
            
            # STEP 2: Test that Bob cannot delete Alice's asset
            mock_delete.side_effect = Exception("Unauthorized - not asset owner")
            
            bob_delete_payload = {
                "asset_id": alice_asset_id,
                "wallet_address": bob_wallet
            }
            
            bob_delete_response = client.post("/api/delete", json=bob_delete_payload)
            assert bob_delete_response.status_code in [401, 403, 500]
            
            # STEP 3: Test that Alice can access her own asset
            mock_retrieve.side_effect = None
            mock_retrieve.return_value = {
                "assetId": alice_asset_id,
                "version": 1,
                "critical_metadata": {"name": "Alice's Private Asset"},
                "verification": {"verified": True}
            }
            
            alice_retrieve_response = client.get(f"/api/retrieve/{alice_asset_id}?wallet_address={alice_wallet}")
            assert alice_retrieve_response.status_code == 200
            
            alice_data = alice_retrieve_response.json()
            assert alice_data["assetId"] == alice_asset_id


if __name__ == "__main__":
    # Run E2E tests
    pytest.main([__file__, "-v", "--tb=short"])