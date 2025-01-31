import os
import json
import pytest
from httpx import AsyncClient
from unittest.mock import patch, MagicMock

# Import app directly from app directory
import sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from app.main import app

@pytest.fixture
def test_data():
    """Load sample test data"""
    test_data_dir = os.path.join(os.path.dirname(__file__), 'test_data')
    samples = {}
    for i in range(1, 4):
        with open(os.path.join(test_data_dir, f'sample{i}.json')) as f:
            samples[f'sample{i}'] = json.load(f)
    return samples

@pytest.fixture
async def async_client():
    """Create async client for testing"""
    async with AsyncClient(app=app, base_url="http://test") as client:
        yield client

@pytest.mark.asyncio
@patch('app.routes.route_sc.web3')
@patch('app.mongodb_client.MongoDBClient')
async def test_store_document_flow(mock_mongo, mock_web3, async_client, test_data):
    """Test the complete flow of storing a document"""
    # Mock MongoDB response
    mock_instance = MagicMock()
    mock_instance.insert_document.return_value = "mocked_doc_id"
    mock_mongo.return_value = mock_instance
    
    # Mock blockchain response
    mock_web3.eth.wait_for_transaction_receipt.return_value = MagicMock(
        transactionHash=b'mocked_tx_hash'
    )

    # Test with sample1
    sample = test_data['sample1']
    
    # First, store CID in blockchain
    response = await async_client.post(
        "/store_cid/",
        json={"cid": sample['ipfs_hash']}
    )
    assert response.status_code == 200
    
    # Then store document in MongoDB
    response = await async_client.post(
        "/db/documents/",
        json={
            "asset_id": sample['asset_id'],
            "user_wallet_address": sample['user_wallet_address'],
            "smart_contract_tx_id": sample['smart_contract_tx_id'],
            "ipfs_hash": sample['ipfs_hash'],
            "critical_metadata": sample['critical_metadata'],
            "non_critical_metadata": sample['non_critical_metadata']
        }
    )
    assert response.status_code == 200
    assert 'document_id' in response.json()

@pytest.mark.asyncio
@patch('app.mongodb_client.MongoDBClient')
async def test_retrieve_document(mock_mongo, async_client, test_data):
    """Test document retrieval"""
    # Mock MongoDB response with sample2
    mock_instance = MagicMock()
    mock_instance.get_document_by_id.return_value = test_data['sample2']
    mock_mongo.return_value = mock_instance

    response = await async_client.get("/db/documents/mocked_doc_id")
    assert response.status_code == 200
    assert response.json()['asset_id'] == test_data['sample2']['asset_id']

@pytest.mark.asyncio
@patch('app.mongodb_client.MongoDBClient')
async def test_get_documents_by_wallet(mock_mongo, async_client, test_data):
    """Test retrieving documents by wallet address"""
    # Mock MongoDB response with sample3
    mock_instance = MagicMock()
    mock_instance.get_documents_by_wallet.return_value = [test_data['sample3']]
    mock_mongo.return_value = mock_instance

    response = await async_client.get(
        f"/db/documents/wallet/{test_data['sample3']['user_wallet_address']}"
    )
    assert response.status_code == 200
    assert len(response.json()['documents']) == 1

@pytest.mark.asyncio
async def test_invalid_document_id(async_client):
    """Test handling of invalid document ID"""
    response = await async_client.get("/db/documents/invalid_id")
    assert response.status_code == 404

@pytest.mark.asyncio
@patch('app.routes.route_sc.web3')
async def test_fetch_cids(mock_web3, async_client):
    """Test fetching CIDs from blockchain"""
    mock_web3.to_checksum_address.return_value = "0x00823FB00C2cDf1841d52bC91affB661Df39466F"
    mock_contract = MagicMock()
    mock_contract.functions.fetchCIDsDigestByAddress().call.return_value = [
        b'mock_cid_1',
        b'mock_cid_2'
    ]
    mock_web3.eth.contract.return_value = mock_contract

    response = await async_client.get(
        "/fetch_cids/?user_address=0x00823FB00C2cDf1841d52bC91affB661Df39466F"
    )
    assert response.status_code == 200
    assert len(response.json()['cids']) > 0