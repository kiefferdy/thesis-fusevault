import sys
import os
import asyncio
from bson import ObjectId
from motor.motor_asyncio import AsyncIOMotorClient

# Add the parent directory to Python path to allow imports from app folder
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.mongodb_client import MongoDBClient

async def cleanup_test_data(db):
    """Delete test data before running the tests"""
    try:
        result = await db.domain_collection.delete_one({"assetId": "test_asset_001"})
        if result.deleted_count:
            print("Cleanup: Deleted test document")
        else:
            print("Cleanup: No test document found to delete")
    except Exception as e:
        print(f"Cleanup: Error deleting test document: {str(e)}")

async def test_mongodb_operations():
    """Test all major MongoDB operations"""
    
    # Initialize MongoDB client
    try:
        db = MongoDBClient()
        
        print("\n=== Starting MongoDB Tests ===\n")
        
        await cleanup_test_data(db)
        
        # Test 1: Insert Document
        print("Test 1: Inserting document...")
        doc_id = await db.insert_document(
            asset_id="test_asset_001",
            user_wallet_address="0x00823FB00C2cDf1841d52bC91affB661Df39466F",
            smart_contract_tx_id="0x369ca86929735eb467c6abcf51b98542b4671b62",
            ipfs_hash="QmTest123",
            critical_metadata={
                "title": "Test Document",
                "type": "Test"
            },
            non_critical_metadata={
                "description": "This is a test document",
                "tags": ["test", "demo"]
            }
        )
        print(f"✓ Document inserted successfully with ID: {doc_id}\n")

        # Test 2: Retrieve Document
        print("Test 2: Retrieving document...")
        document = await db.get_document_by_id(doc_id)
        print(f"✓ Retrieved document: {document}\n")

        # Test 3: Update Document
        print("Test 3: Updating document...")
        updated = await db.update_document(
            document_id=doc_id,
            smart_contract_tx_id="0x369ca86929735eb467c6abcf51b98542b4671b62",
            ipfs_hash="QmTest124",
            critical_metadata={
                "title": "Updated Test Document",
                "type": "Test"
            },
            non_critical_metadata={
                "description": "This is an updated test document",
                "tags": ["test", "demo", "updated"]
            }
        )
        print(f"✓ Document updated successfully: {updated}\n")

        # Test 4: Retrieve Updated Document
        print("Test 4: Retrieving updated document...")
        updated_document = await db.get_document_by_id(doc_id)
        print(f"✓ Retrieved updated document: {updated_document}\n")

        # Test 5: Get Documents by Wallet
        print("Test 5: Retrieving documents by wallet address...")
        wallet_docs = await db.get_documents_by_wallet("0x00823FB00C2cDf1841d52bC91affB661Df39466F")
        print(f"✓ Found {len(wallet_docs)} documents for wallet\n")

        # Test 6: Verify Document
        print("Test 6: Verifying document...")
        verified = await db.verify_document(doc_id)
        print(f"✓ Document verification status: {verified}\n")

        # Test 7: Soft Delete Document
        print("Test 7: Soft deleting document...")
        deleted = await db.soft_delete(doc_id)
        print(f"✓ Document soft deletion status: {deleted}\n")

        print("=== All tests completed successfully ===\n")

    except Exception as e:
        print(f"\n❌ Error during testing: {str(e)}")
    finally:
        if 'db' in locals():
            await db.close_connection()
            print("MongoDB connection closed")

if __name__ == "__main__":
    asyncio.run(test_mongodb_operations())