import os
import json
import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock
from bson import ObjectId

# Import app directly from app directory
import sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))
from app.main import app

@pytest.fixture
def test_data():
    """Load sample test data"""
    test_data_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '../..', 'test_data'))
    samples = {}
    for i in range(1, 4):
        with open(os.path.join(test_data_dir, f'sample{i}.json')) as f:
            samples[f'sample{i}'] = json.load(f)
    return samples

@pytest.fixture
def client():
    """Create test client"""
    return TestClient(app)

@patch('app.routes.route_db.MongoDBClient')
def test_store_document_flow(mock_mongo, client, test_data):
    """Test storing a document in MongoDB"""
    # Mock MongoDB response
    mock_instance = MagicMock()
    mock_instance.insert_document.return_value = "mocked_doc_id"
    mock_mongo.return_value = mock_instance
    
    # Test with sample1
    sample = test_data['sample1']
    
    # Store document in MongoDB
    doc_data = {
        "asset_id": sample['asset_id'],
        "user_wallet_address": sample['user_wallet_address'],
        "smart_contract_tx_id": sample['smart_contract_tx_id'],
        "ipfs_hash": sample['ipfs_hash'],
        "critical_metadata": sample['critical_metadata'],
        "non_critical_metadata": sample['non_critical_metadata']
    }
    
    response = client.post("/db/documents", json=doc_data)
    assert response.status_code == 200
    assert 'document_id' in response.json()

@patch('app.routes.route_db.MongoDBClient')
def test_retrieve_document(mock_mongo, client, test_data):
    """Test document retrieval"""
    # Create a valid MongoDB ObjectId
    mock_id = str(ObjectId())
    
    # Mock MongoDB response with sample2
    mock_instance = MagicMock()
    sample2_with_id = test_data['sample2'].copy()
    sample2_with_id['_id'] = mock_id
    mock_instance.get_document_by_id.return_value = sample2_with_id
    mock_mongo.return_value = mock_instance

    response = client.get(f"/db/documents/{mock_id}")
    print(f"Response: {response.json()}")  # Add debug print
    assert response.status_code == 200
    assert response.json()['asset_id'] == test_data['sample2']['asset_id']

@patch('app.routes.route_db.MongoDBClient')
def test_get_documents_by_wallet(mock_mongo, client, test_data):
    """Test retrieving documents by wallet address"""
    # Mock MongoDB response with sample3
    mock_instance = MagicMock()
    # Add _id to the sample data
    sample3_with_id = test_data['sample3'].copy()
    sample3_with_id['_id'] = str(ObjectId())
    mock_instance.get_documents_by_wallet.return_value = [sample3_with_id]
    mock_mongo.return_value = mock_instance

    response = client.get(
        f"/db/documents/wallet/{test_data['sample3']['user_wallet_address']}"
    )
    print(f"Wallet response: {response.json()}")  # Add debug print
    data = response.json()
    assert response.status_code == 200
    assert 'documents' in data
    assert len(data['documents']) == 1

def test_invalid_document_id(client):
    """Test handling of invalid document ID"""
    response = client.get("/db/documents/invalid_id")
    assert response.status_code == 404

@patch('app.routes.route_sc.web3')
def test_fetch_cids(mock_web3, client):
    """Test fetching CIDs from blockchain"""
    mock_web3.to_checksum_address.return_value = "0x00823FB00C2cDf1841d52bC91affB661Df39466F"
    mock_contract = MagicMock()
    mock_contract.functions.fetchCIDsDigestByAddress().call.return_value = [
        b'mock_cid_1',
        b'mock_cid_2'
    ]
    mock_web3.eth.contract.return_value = mock_contract

    response = client.get(
        "/fetch_cids/?user_address=0x00823FB00C2cDf1841d52bC91affB661Df39466F"
    )
    assert response.status_code == 200
    assert len(response.json()['cids']) > 0

@patch('app.mongodb_client.MongoDBClient')
def test_update_document(mock_mongo, client, test_data):
    """Test document update"""
    # Mock MongoDB response
    mock_instance = MagicMock()
    mock_instance.update_document.return_value = True
    mock_mongo.return_value = mock_instance

    sample = test_data['sample1']
    response = client.put(
        "/db/documents/mocked_doc_id",
        params={
            "smart_contract_tx_id": sample['smart_contract_tx_id'],
            "ipfs_hash": sample['ipfs_hash']
        },
        json={
            "critical_metadata": sample['critical_metadata'],
            "non_critical_metadata": sample['non_critical_metadata']
        }
    )
    assert response.status_code == 200
    assert response.json()['status'] == 'success'

@patch('app.mongodb_client.MongoDBClient')
def test_verify_document(mock_mongo, client):
    """Test document verification"""
    # Mock MongoDB instance properly
    mock_instance = MagicMock()
    mock_instance.verify_document.return_value = True
    mock_mongo.return_value = mock_instance
    
    # Ensure the mock is properly replacing the original class
    with patch('app.routes.route_db.MongoDBClient', return_value=mock_instance):
        response = client.post("/db/documents/mocked_doc_id/verify")
        assert response.status_code == 200
        assert response.json()['status'] == 'success'

@patch('app.mongodb_client.MongoDBClient')
def test_delete_document(mock_mongo, client):
    """Test document deletion"""
    # Mock MongoDB instance properly
    mock_instance = MagicMock()
    mock_instance.soft_delete.return_value = True
    mock_mongo.return_value = mock_instance
    
    # Ensure the mock is properly replacing the original class
    with patch('app.routes.route_db.MongoDBClient', return_value=mock_instance):
        response = client.delete("/db/documents/mocked_doc_id")
        assert response.status_code == 200
        assert response.json()['status'] == 'success'