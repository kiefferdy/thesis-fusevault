import pytest
from unittest.mock import AsyncMock, MagicMock
from datetime import datetime

from app.repositories.delegation_repo import DelegationRepository
from app.database import MockCollection


class TestDelegationRepository:
    """Test suite for delegation repository operations."""

    @pytest.fixture
    def mock_db_client(self):
        """Create a mock database client with delegation collection."""
        mock_client = MagicMock()
        mock_client.delegations_collection = MockCollection("delegations")
        return mock_client

    @pytest.fixture
    def delegation_repo(self, mock_db_client):
        """Create a delegation repository instance."""
        return DelegationRepository(mock_db_client)

    @pytest.mark.asyncio
    async def test_create_indexes(self, delegation_repo):
        """Test creating indexes for delegation collection."""
        result = await delegation_repo.create_indexes()
        # Mock implementation returns list of index names
        assert isinstance(result, list)

    @pytest.mark.asyncio
    async def test_upsert_delegation_new(self, delegation_repo):
        """Test upserting a new delegation."""
        delegation_data = {
            "ownerAddress": "0x1234567890123456789012345678901234567890",
            "delegateAddress": "0x0987654321098765432109876543210987654321",
            "isActive": True,
            "transactionHash": "0xabcdef",
            "blockNumber": 12345
        }
        
        delegation_id = await delegation_repo.upsert_delegation(delegation_data)
        
        assert delegation_id is not None
        assert isinstance(delegation_id, str)

    @pytest.mark.asyncio
    async def test_upsert_delegation_update_existing(self, delegation_repo):
        """Test upserting an existing delegation (update)."""
        # First insert a delegation
        delegation_data = {
            "ownerAddress": "0x1234567890123456789012345678901234567890",
            "delegateAddress": "0x0987654321098765432109876543210987654321",
            "isActive": True,
            "transactionHash": "0xabcdef",
            "blockNumber": 12345
        }
        
        first_id = await delegation_repo.upsert_delegation(delegation_data)
        
        # Update the same delegation
        delegation_data_update = {
            "ownerAddress": "0x1234567890123456789012345678901234567890",
            "delegateAddress": "0x0987654321098765432109876543210987654321",
            "isActive": False,  # Change status
            "transactionHash": "0x123456",
            "blockNumber": 12346
        }
        
        second_id = await delegation_repo.upsert_delegation(delegation_data_update)
        
        # Should update existing delegation, not create new one
        assert second_id is not None

    @pytest.mark.asyncio
    async def test_get_delegations_by_owner_empty(self, delegation_repo):
        """Test getting delegations when owner has no delegates."""
        owner_address = "0x1234567890123456789012345678901234567890"
        
        delegations = await delegation_repo.get_delegations_by_owner(owner_address)
        
        assert delegations == []

    @pytest.mark.asyncio
    async def test_get_delegations_by_owner_with_data(self, delegation_repo):
        """Test getting delegations when owner has delegates."""
        owner_address = "0x1234567890123456789012345678901234567890"
        delegate_address = "0x0987654321098765432109876543210987654321"
        
        # Insert a delegation
        delegation_data = {
            "ownerAddress": owner_address,
            "delegateAddress": delegate_address,
            "isActive": True,
            "transactionHash": "0xabcdef",
            "blockNumber": 12345
        }
        
        await delegation_repo.upsert_delegation(delegation_data)
        
        # Get delegations
        delegations = await delegation_repo.get_delegations_by_owner(owner_address)
        
        assert len(delegations) == 1
        assert delegations[0]["ownerAddress"] == owner_address
        assert delegations[0]["delegateAddress"] == delegate_address
        assert delegations[0]["isActive"] is True
        assert "id" in delegations[0]

    @pytest.mark.asyncio
    async def test_get_delegations_by_delegate_empty(self, delegation_repo):
        """Test getting delegations when delegate has no delegators."""
        delegate_address = "0x0987654321098765432109876543210987654321"
        
        delegations = await delegation_repo.get_delegations_by_delegate(delegate_address)
        
        assert delegations == []

    @pytest.mark.asyncio
    async def test_get_delegations_by_delegate_with_data(self, delegation_repo):
        """Test getting delegations when delegate has delegators."""
        owner_address = "0x1234567890123456789012345678901234567890"
        delegate_address = "0x0987654321098765432109876543210987654321"
        
        # Insert a delegation
        delegation_data = {
            "ownerAddress": owner_address,
            "delegateAddress": delegate_address,
            "isActive": True,
            "transactionHash": "0xabcdef",
            "blockNumber": 12345
        }
        
        await delegation_repo.upsert_delegation(delegation_data)
        
        # Get delegations
        delegations = await delegation_repo.get_delegations_by_delegate(delegate_address)
        
        assert len(delegations) == 1
        assert delegations[0]["ownerAddress"] == owner_address
        assert delegations[0]["delegateAddress"] == delegate_address
        assert delegations[0]["isActive"] is True
        assert "id" in delegations[0]

    @pytest.mark.asyncio
    async def test_get_delegation_exists(self, delegation_repo):
        """Test getting a specific delegation that exists."""
        owner_address = "0x1234567890123456789012345678901234567890"
        delegate_address = "0x0987654321098765432109876543210987654321"
        
        # Insert a delegation
        delegation_data = {
            "ownerAddress": owner_address,
            "delegateAddress": delegate_address,
            "isActive": True,
            "transactionHash": "0xabcdef",
            "blockNumber": 12345
        }
        
        await delegation_repo.upsert_delegation(delegation_data)
        
        # Get specific delegation
        delegation = await delegation_repo.get_delegation(owner_address, delegate_address)
        
        assert delegation is not None
        assert delegation["ownerAddress"] == owner_address.lower()
        assert delegation["delegateAddress"] == delegate_address.lower()
        assert delegation["isActive"] is True
        assert "id" in delegation

    @pytest.mark.asyncio
    async def test_get_delegation_not_exists(self, delegation_repo):
        """Test getting a specific delegation that doesn't exist."""
        owner_address = "0x1234567890123456789012345678901234567890"
        delegate_address = "0x0987654321098765432109876543210987654321"
        
        # Get specific delegation (should not exist)
        delegation = await delegation_repo.get_delegation(owner_address, delegate_address)
        
        assert delegation is None

    @pytest.mark.asyncio
    async def test_update_delegation_status_exists(self, delegation_repo):
        """Test updating delegation status for existing delegation."""
        owner_address = "0x1234567890123456789012345678901234567890"
        delegate_address = "0x0987654321098765432109876543210987654321"
        
        # Insert a delegation
        delegation_data = {
            "ownerAddress": owner_address,
            "delegateAddress": delegate_address,
            "isActive": True,
            "transactionHash": "0xabcdef",
            "blockNumber": 12345
        }
        
        await delegation_repo.upsert_delegation(delegation_data)
        
        # Update status
        success = await delegation_repo.update_delegation_status(
            owner_address, delegate_address, False, "0x123456", 12346
        )
        
        assert success is True
        
        # Verify update
        delegation = await delegation_repo.get_delegation(owner_address, delegate_address)
        assert delegation["isActive"] is False
        assert delegation["transactionHash"] == "0x123456"
        assert delegation["blockNumber"] == 12346

    @pytest.mark.asyncio
    async def test_update_delegation_status_not_exists(self, delegation_repo):
        """Test updating delegation status for non-existing delegation."""
        owner_address = "0x1234567890123456789012345678901234567890"
        delegate_address = "0x0987654321098765432109876543210987654321"
        
        # Update status (should fail)
        success = await delegation_repo.update_delegation_status(
            owner_address, delegate_address, False
        )
        
        assert success is False

    @pytest.mark.asyncio
    async def test_delete_delegation_exists(self, delegation_repo):
        """Test deleting existing delegation."""
        owner_address = "0x1234567890123456789012345678901234567890"
        delegate_address = "0x0987654321098765432109876543210987654321"
        
        # Insert a delegation
        delegation_data = {
            "ownerAddress": owner_address,
            "delegateAddress": delegate_address,
            "isActive": True,
            "transactionHash": "0xabcdef",
            "blockNumber": 12345
        }
        
        await delegation_repo.upsert_delegation(delegation_data)
        
        # Delete delegation
        success = await delegation_repo.delete_delegation(owner_address, delegate_address)
        
        assert success is True
        
        # Verify deletion
        delegation = await delegation_repo.get_delegation(owner_address, delegate_address)
        assert delegation is None

    @pytest.mark.asyncio
    async def test_delete_delegation_not_exists(self, delegation_repo):
        """Test deleting non-existing delegation."""
        owner_address = "0x1234567890123456789012345678901234567890"
        delegate_address = "0x0987654321098765432109876543210987654321"
        
        # Delete delegation (should fail)
        success = await delegation_repo.delete_delegation(owner_address, delegate_address)
        
        assert success is False

    @pytest.mark.asyncio
    async def test_get_delegation_stats(self, delegation_repo):
        """Test getting delegation statistics for a wallet."""
        wallet_address = "0x1234567890123456789012345678901234567890"
        delegate_address = "0x0987654321098765432109876543210987654321"
        another_address = "0x1111111111111111111111111111111111111111"
        
        # Insert delegation where wallet is owner
        delegation_data_1 = {
            "ownerAddress": wallet_address,
            "delegateAddress": delegate_address,
            "isActive": True,
            "transactionHash": "0xabcdef",
            "blockNumber": 12345
        }
        
        # Insert delegation where wallet is delegate
        delegation_data_2 = {
            "ownerAddress": another_address,
            "delegateAddress": wallet_address,
            "isActive": True,
            "transactionHash": "0x123456",
            "blockNumber": 12346
        }
        
        await delegation_repo.upsert_delegation(delegation_data_1)
        await delegation_repo.upsert_delegation(delegation_data_2)
        
        # Get stats
        stats = await delegation_repo.get_delegation_stats(wallet_address)
        
        assert stats["total_delegations"] == 2
        assert stats["delegations_granted"] == 1
        assert stats["delegations_received"] == 1

    @pytest.mark.asyncio
    async def test_sync_from_blockchain_event(self, delegation_repo):
        """Test syncing delegation from blockchain event."""
        event_data = {
            "owner_address": "0x1234567890123456789012345678901234567890",
            "delegate_address": "0x0987654321098765432109876543210987654321",
            "status": True,
            "transaction_hash": "0xabcdef",
            "block_number": 12345
        }
        
        delegation_id = await delegation_repo.sync_from_blockchain_event(event_data)
        
        assert delegation_id is not None
        
        # Verify synced data
        delegation = await delegation_repo.get_delegation(
            event_data["owner_address"], 
            event_data["delegate_address"]
        )
        
        assert delegation is not None
        assert delegation["isActive"] is True
        assert delegation["transactionHash"] == "0xabcdef"
        assert delegation["blockNumber"] == 12345

    @pytest.mark.asyncio 
    async def test_filter_active_only(self, delegation_repo):
        """Test filtering only active delegations."""
        owner_address = "0x1234567890123456789012345678901234567890"
        delegate_address_1 = "0x0987654321098765432109876543210987654321"
        delegate_address_2 = "0x1111111111111111111111111111111111111111"
        
        # Insert active delegation
        delegation_data_1 = {
            "ownerAddress": owner_address,
            "delegateAddress": delegate_address_1,
            "isActive": True,
            "transactionHash": "0xabcdef",
            "blockNumber": 12345
        }
        
        # Insert inactive delegation
        delegation_data_2 = {
            "ownerAddress": owner_address,
            "delegateAddress": delegate_address_2,
            "isActive": False,
            "transactionHash": "0x123456",
            "blockNumber": 12346
        }
        
        await delegation_repo.upsert_delegation(delegation_data_1)
        await delegation_repo.upsert_delegation(delegation_data_2)
        
        # Get only active delegations
        active_delegations = await delegation_repo.get_delegations_by_owner(owner_address, active_only=True)
        
        assert len(active_delegations) == 1
        assert active_delegations[0]["delegateAddress"] == delegate_address_1.lower()
        assert active_delegations[0]["isActive"] is True
        
        # Get all delegations
        all_delegations = await delegation_repo.get_delegations_by_owner(owner_address, active_only=False)
        
        assert len(all_delegations) == 2