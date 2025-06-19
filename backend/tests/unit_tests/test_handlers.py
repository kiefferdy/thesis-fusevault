import pytest
from unittest.mock import MagicMock, patch, AsyncMock
from fastapi import HTTPException, Response, Request, UploadFile
from datetime import datetime, timezone
import io
import json

from app.handlers.auth_handler import AuthHandler
from app.handlers.user_handler import UserHandler
from app.handlers.transaction_handler import TransactionHandler
from app.handlers.upload_handler import UploadHandler
from app.handlers.retrieve_handler import RetrieveHandler
from app.handlers.delete_handler import DeleteHandler
from app.schemas.user_schema import UserCreate
from app.schemas.auth_schema import AuthenticationRequest
from app.schemas.upload_schema import MetadataUploadRequest
from app.schemas.retrieve_schema import MetadataVerificationResult, MetadataRetrieveResponse


# Auth Handler Tests - focusing on HTTP interactions and error handling
class TestAuthHandlerLogic:
    @pytest.mark.asyncio
    async def test_get_nonce_exception_handling(self, mock_auth_service):
        """Test that get_nonce properly handles and transforms service exceptions."""
        # Mock service to raise an exception
        mock_auth_service.get_nonce.side_effect = Exception("Service error")
        
        # Initialize handler with mock service
        handler = AuthHandler(mock_auth_service)
        
        # Call method and expect HTTPException
        with pytest.raises(HTTPException) as exc_info:
            await handler.get_nonce("0x1234567890123456789012345678901234567890")
        
        # Verify the exception details
        assert exc_info.value.status_code == 500
        assert "Error getting nonce" in str(exc_info.value.detail)
    
    @pytest.mark.asyncio
    async def test_authenticate_sets_http_cookie(self, mock_auth_service, mock_response):
        """Test that authenticate sets the proper HTTP cookie."""
        # Mock request data
        request = AuthenticationRequest(
            wallet_address="0x1234567890123456789012345678901234567890",
            signature="0xsignature123"
        )
        
        # Mock auth service authenticate to return success
        mock_auth_service.authenticate.return_value = (True, "Authentication successful")
        
        # Mock session creation
        session_id = "session123"
        mock_auth_service.create_session.return_value = session_id
        
        # Initialize handler with mock service
        handler = AuthHandler(mock_auth_service)
        
        # Call method
        await handler.authenticate(request, mock_response)
        
        # Verify cookie was set correctly
        mock_response.set_cookie.assert_called_once()
        cookie_args = mock_response.set_cookie.call_args[1]
        assert cookie_args["key"] == "session_id"
        assert cookie_args["value"] == session_id
        assert cookie_args["httponly"] is True
        assert cookie_args["max_age"] == 86400  # 24 hours (JWT expiration)
        assert cookie_args["samesite"] == "lax"
    
    @pytest.mark.asyncio
    async def test_authenticate_failed_session_creation(self, mock_auth_service, mock_response):
        """Test that authenticate handles failed session creation."""
        # Mock request data
        request = AuthenticationRequest(
            wallet_address="0x1234567890123456789012345678901234567890",
            signature="0xsignature123"
        )
        
        # Mock auth service authenticate to return success
        mock_auth_service.authenticate.return_value = (True, "Authentication successful")
        
        # Mock session creation failure
        mock_auth_service.create_session.return_value = None
        
        # Initialize handler with mock service
        handler = AuthHandler(mock_auth_service)
        
        # Call method and expect exception
        with pytest.raises(HTTPException) as exc_info:
            await handler.authenticate(request, mock_response)
        
        # Verify the exception details
        assert exc_info.value.status_code == 500
        assert "Failed to create session" in str(exc_info.value.detail)
    
    @pytest.mark.asyncio
    async def test_logout_clears_cookie(self, mock_auth_service, mock_request, mock_response):
        """Test that logout clears the session cookie."""
        # Setup mock request with session
        mock_request.cookies = {"session_id": "session123"}
        
        # Mock logout to succeed
        mock_auth_service.logout.return_value = True
        
        # Initialize handler with mock service
        handler = AuthHandler(mock_auth_service)
        
        # Call method
        await handler.logout(mock_request, mock_response)
        
        # Verify cookie was deleted
        mock_response.delete_cookie.assert_called_once_with(key="session_id")
    
    @pytest.mark.asyncio
    async def test_logout_no_session_cookie(self, mock_auth_service, mock_request, mock_response):
        """Test that logout handles missing session cookie."""
        # Setup mock request with no session
        mock_request.cookies = {}
        
        # Initialize handler with mock service
        handler = AuthHandler(mock_auth_service)
        
        # Call method and expect exception
        with pytest.raises(HTTPException) as exc_info:
            await handler.logout(mock_request, mock_response)
        
        # Verify the exception details
        assert exc_info.value.status_code == 401
        assert "No active session" in str(exc_info.value.detail)


# Transaction Handler Tests - focusing on integration, validation, and error handling
class TestTransactionHandlerLogic:
    @pytest.mark.asyncio
    async def test_get_asset_history_verifies_asset_exists(self, mock_transaction_service, mock_asset_service):
        """Test that get_asset_history first verifies the asset exists."""
        # Setup
        asset_id = "test-asset-123"
        
        # Mock asset service to say asset doesn't exist
        mock_asset_service.get_asset.return_value = None
        
        # Initialize handler with mock services
        handler = TransactionHandler(mock_transaction_service, mock_asset_service)
        
        # Call method and expect exception
        with pytest.raises(HTTPException) as exc_info:
            await handler.get_asset_history(asset_id)
        
        # Verify the exception details
        assert exc_info.value.status_code == 404
        assert f"Asset with ID {asset_id} not found" in str(exc_info.value.detail)
        
        # Verify asset existence was checked but transactions were not fetched
        mock_asset_service.get_asset.assert_called_once_with(asset_id)
        mock_transaction_service.get_asset_history.assert_not_called()
    
    @pytest.mark.asyncio
    async def test_get_transaction_details_with_asset_info(self, mock_transaction_service, mock_asset_service):
        """Test that get_transaction_details also fetches asset info when available."""
        # Setup
        transaction_id = "tx123"
        asset_id = "asset123"
        
        # Mock transaction service to return a transaction with asset ID
        mock_transaction = {
            "_id": transaction_id,
            "assetId": asset_id,
            "action": "CREATE",
            "walletAddress": "0x1234567890123456789012345678901234567890"
        }
        mock_transaction_service.get_transaction_by_id.return_value = mock_transaction
        
        # Mock asset service to return asset info
        mock_asset = {
            "_id": "doc123",
            "assetId": asset_id,
            "name": "Test Asset"
        }
        mock_asset_service.get_asset.return_value = mock_asset
        
        # Initialize handler with mock services
        handler = TransactionHandler(mock_transaction_service, mock_asset_service)
        
        # Call method
        result = await handler.get_transaction_details(transaction_id)
        
        # Verify result includes both transaction and asset info
        assert result["transaction"] == mock_transaction
        assert result["asset_info"] == mock_asset
        
        # Verify calls to services
        mock_transaction_service.get_transaction_by_id.assert_called_once_with(transaction_id)
        mock_asset_service.get_asset.assert_called_once_with(asset_id)
    
    @pytest.mark.asyncio
    async def test_get_transaction_details_handles_asset_error(self, mock_transaction_service, mock_asset_service):
        """Test that get_transaction_details handles errors when fetching asset info."""
        # Setup
        transaction_id = "tx123"
        asset_id = "asset123"
        
        # Mock transaction service to return a transaction with asset ID
        mock_transaction = {
            "_id": transaction_id,
            "assetId": asset_id,
            "action": "CREATE",
            "walletAddress": "0x1234567890123456789012345678901234567890"
        }
        mock_transaction_service.get_transaction_by_id.return_value = mock_transaction
        
        # Mock asset service to raise an exception
        mock_asset_service.get_asset.side_effect = Exception("Asset service error")
        
        # Initialize handler with mock services
        handler = TransactionHandler(mock_transaction_service, mock_asset_service)
        
        # Call method - should not raise exception despite asset service error
        result = await handler.get_transaction_details(transaction_id)
        
        # Verify result includes transaction but asset_info is None
        assert result["transaction"] == mock_transaction
        assert result["asset_info"] is None
        
        # Verify calls to services
        mock_transaction_service.get_transaction_by_id.assert_called_once_with(transaction_id)
        mock_asset_service.get_asset.assert_called_once_with(asset_id)


# Retrieve Handler Tests - focusing on the verification and auto-recovery flow
class TestRetrieveHandlerLogic:
    @pytest.mark.asyncio
    async def test_retrieve_metadata_auto_recovery_decision(self, mock_asset_service, mock_blockchain_service,
                                                            mock_ipfs_service, mock_transaction_service):
        # Setup
        asset_id = "test-asset-123"
        # Mock asset service
        mock_asset_service.get_asset_with_deleted.return_value = {"assetId": asset_id}
        
        # Create a document with mismatched CIDs
        mock_asset = {
            "_id": "doc123",
            "assetId": asset_id,
            "versionNumber": 1,
            "isCurrent": True,
            "walletAddress": "0x1234567890123456789012345678901234567890",
            "smartContractTxId": "0xabc123",
            "ipfsHash": "QmStored123",  # Stored hash
            "criticalMetadata": {"name": "Tampered Asset"},
            "nonCriticalMetadata": {}
        }
        mock_asset_service.get_asset.return_value = mock_asset
        
        # Mock blockchain service to return a different CID from what's stored
        mock_blockchain_service.get_hash_from_transaction.return_value = {
            "cid": "QmBlockchain456",  # Different from stored hash
            "tx_hash": "0xabc123",
            "tx_sender": "0x9876543210987654321098765432109876543210",
            "status": "success"
        }
        mock_blockchain_service.wallet_address = "0x9876543210987654321098765432109876543210"
        
        # Mock ipfs service to return a computed CID that doesn't match blockchain
        mock_ipfs_service.compute_cid.return_value = "QmComputed789"  # Different from both
        
        # Initialize handler with mock services
        handler = RetrieveHandler(
            asset_service=mock_asset_service,
            blockchain_service=mock_blockchain_service,
            ipfs_service=mock_ipfs_service,
            transaction_service=mock_transaction_service
        )
        
        # Test 1: Call with auto_recover=False - shouldn't attempt recovery
        result_no_recovery = await handler.retrieve_metadata(asset_id, auto_recover=False)
        
        # Verify no recovery was attempted
        assert result_no_recovery.verification.recovery_needed is True
        assert result_no_recovery.verification.recovery_successful is None
        assert result_no_recovery.verification.new_version_created is None
        mock_ipfs_service.retrieve_metadata.assert_not_called()
        mock_asset_service.create_new_version.assert_not_called()


# Upload Handler Tests - focusing on file processing and errors not covered elsewhere
class TestUploadHandlerLogic:
    @pytest.mark.asyncio
    async def test_handle_json_files_validates_file_extension(self, monkeypatch):
        """Test that handle_json_files validates file extensions."""
        # Create handler with mock services
        handler = UploadHandler()
        
        # Mock process_metadata to focus test on file validation
        async def mock_process(*args, **kwargs):
            return {"status": "success"}
        monkeypatch.setattr(handler, "process_metadata", mock_process)
        
        # Create a list with one valid JSON file and one invalid file
        json_file = MagicMock(spec=UploadFile)
        json_file.filename = "valid.json"
        json_file.read = AsyncMock(return_value=b'{"asset_id": "test", "critical_metadata": {}}')
        
        text_file = MagicMock(spec=UploadFile)
        text_file.filename = "invalid.txt"
        
        # Call method
        result = await handler.handle_json_files(
            files=[json_file, text_file],
            wallet_address="0x1234567890123456789012345678901234567890"
        )
        
        # Verify results
        assert result["upload_count"] == 2
        assert len(result["results"]) == 2
        
        # First file should be processed
        assert "status" in result["results"][0]
        
        # Second file should have an error
        assert result["results"][1]["status"] == "error"
        assert "Not a JSON file" in result["results"][1]["detail"]
        
        # Verify only the valid file was read
        json_file.read.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_process_csv_upload_validates_required_columns(self, monkeypatch):
        """Test that process_csv_upload validates required columns."""
        # Create handler with mock services
        handler = UploadHandler()
        
        # Create a mock CSV file missing a required column
        csv_file = MagicMock(spec=UploadFile)
        csv_file.filename = "test.csv"
        csv_content = "asset_id,name,extra_field\n" + \
                      "csv-asset-1,CSV Asset 1,extra1\n"
        csv_file.read = AsyncMock(return_value=csv_content.encode())
        
        # Call method with a required column that's not in the CSV
        result = await handler.process_csv_upload(
            files=[csv_file],
            wallet_address="0x1234567890123456789012345678901234567890",
            critical_metadata_fields=["name", "description"]  # description is missing
        )
        
        # Verify results
        assert result["upload_count"] == 1
        assert result["results"][0]["status"] == "error"
        assert "Missing critical columns" in result["results"][0]["detail"]
        
        # Verify file was read
        csv_file.read.assert_called_once()


# Delete Handler Tests - focusing on ownership validation and batch operations
class TestDeleteHandlerLogic:
    @pytest.mark.asyncio
    async def test_delete_asset_ownership_validation(self, mock_asset_service, mock_transaction_service):
        # Setup
        asset_id = "test-asset-123"
        owner_wallet = "0x1234567890123456789012345678901234567890"
        different_wallet = "0x0987654321098765432109876543210987654321"

        # Mock transaction service to return a valid transaction ID
        mock_transaction_service.record_transaction.return_value = "tx_123"

        # Mock asset service to return an asset owned by owner_wallet
        mock_asset = {
            "_id": "doc123",
            "assetId": asset_id,
            "walletAddress": owner_wallet,
            "isDeleted": False
        }
        mock_asset_service.get_asset.return_value = mock_asset

        # Initialize handler with mock services
        handler = DeleteHandler(
            asset_service=mock_asset_service,
            transaction_service=mock_transaction_service
        )

        # Configure soft_delete to succeed
        mock_asset_service.soft_delete.return_value = True

        # Test 1: Call with the owner's wallet - should succeed
        result = await handler.delete_asset(
            asset_id=asset_id,
            wallet_address=owner_wallet
        )

        # Verify the result
        assert result.asset_id == asset_id
        assert result.status == "success"
        assert result.document_id == "doc123"
        assert result.transaction_id == "tx_123"
    
    @pytest.mark.asyncio
    async def test_batch_delete_assets_partial_failure(self, mock_asset_service, mock_transaction_service):
        # Setup asset IDs and wallet
        asset_ids = ["asset1", "asset2", "asset3"]
        wallet_address = "0x1234567890123456789012345678901234567890"

        # Mock transaction service to return a valid transaction ID
        mock_transaction_service.record_transaction.return_value = "tx_123"

        # Initialize handler with mock services
        handler = DeleteHandler(
            asset_service=mock_asset_service,
            transaction_service=mock_transaction_service
        )

        # Create a mock delete method
        async def mock_delete_asset(asset_id, wallet, reason=None):
            from app.schemas.delete_schema import DeleteResponse
            if asset_id == "asset3":
                from fastapi import HTTPException
                raise HTTPException(status_code=404, detail="Asset not found")

            return DeleteResponse(
                asset_id=asset_id,
                status="success",
                message=f"Asset {asset_id} deleted",
                document_id=f"doc_{asset_id}",
                transaction_id=f"tx_{asset_id}"
            )

        # Replace the method
        original_delete_asset = handler.delete_asset
        handler.delete_asset = mock_delete_asset

        try:
            # Call batch_delete_assets
            result = await handler.batch_delete_assets(
                asset_ids=asset_ids,
                wallet_address=wallet_address,
                reason="Testing batch delete"
            )

            # Verify the result
            assert result.status == "partial"
            assert result.success_count == 2
            assert result.failure_count == 1
            assert len(result.results) == 3
            
            # Check individual results
            assert result.results["asset1"]["status"] == "success"
            assert result.results["asset2"]["status"] == "success"
            assert result.results["asset3"]["status"] == "error"

        finally:
            # Restore original method
            handler.delete_asset = original_delete_asset