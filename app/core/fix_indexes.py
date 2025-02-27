# For composite key of Version and Asset ID don't delete yet still making sure it's not needed - Tim

import os
import sys
import logging
from dotenv import load_dotenv

# Add the project root to the path so we can import from app
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Import your MongoDBClient
from app.core.mongodb_client import MongoDBClient

def fix_index_for_versioning():
    """Fix the index on assets collection to support document versioning."""
    try:
        # Initialize the MongoDB client
        load_dotenv()
        db_client = MongoDBClient()
        
        # List existing indexes
        print("Existing indexes:")
        for idx in db_client.assets_collection.list_indexes():
            print(f"  - {idx['name']}: {idx['key']}")
        
        # Drop the existing single-field index on assetId
        print("\nDropping existing index on assetId...")
        db_client.assets_collection.drop_index("assetId_1")
        
        # Create the compound index
        print("Creating compound index on assetId and versionNumber...")
        db_client.assets_collection.create_index(
            [("assetId", 1), ("versionNumber", 1)], 
            unique=True
        )
        
        # List updated indexes
        print("\nUpdated indexes:")
        for idx in db_client.assets_collection.list_indexes():
            print(f"  - {idx['name']}: {idx['key']}")
        
        print("\nSuccessfully updated index structure.")
        return True
    except Exception as e:
        print(f"\nError fixing index: {str(e)}")
        return False

if __name__ == "__main__":
    fix_index_for_versioning()