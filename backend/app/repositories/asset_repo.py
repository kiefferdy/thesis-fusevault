from typing import Dict, Any, List, Optional
from pymongo import DESCENDING
import logging

logger = logging.getLogger(__name__)

class AssetRepository:
    """
    Repository for asset operations in MongoDB.
    Handles CRUD operations for the assets collection.
    """
    
    def __init__(self, db_client):
        """
        Initialize with MongoDB client.
        
        Args:
            db_client: The MongoDB client with initialized collections
        """
        self.assets_collection = db_client.assets_collection
        
    async def insert_asset(self, document: Dict[str, Any]) -> str:
        """
        Insert a new asset document.
        
        Args:
            document: The document to insert
            
        Returns:
            String ID of the inserted document
        """
        try:
            result = self.assets_collection.insert_one(document)
            doc_id = str(result.inserted_id)
            
            logger.info(f"Asset document inserted with ID: {doc_id}")
            return doc_id
            
        except Exception as e:
            logger.error(f"Error inserting asset: {str(e)}")
            raise
            
    async def find_asset(self, query: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Find an asset by query parameters.
        
        Args:
            query: The query parameters to search by
            
        Returns:
            Asset document if found, None otherwise
        """
        try:
            # Find the document
            asset = self.assets_collection.find_one(query)
            
            # Convert ObjectId to string if asset found
            if asset:
                asset["_id"] = str(asset["_id"])
                
            return asset
            
        except Exception as e:
            logger.error(f"Error finding asset: {str(e)}")
            raise
            
    async def find_assets(self, query: Dict[str, Any], sort_field: str = "lastUpdated", sort_direction: int = DESCENDING) -> List[Dict[str, Any]]:
        """
        Find assets by query parameters.
        
        Args:
            query: The query parameters to search by
            sort_field: Field to sort by (default: lastUpdated)
            sort_direction: Direction to sort (default: DESCENDING)
            
        Returns:
            List of asset documents
        """
        try:
            # Find the documents
            cursor = self.assets_collection.find(query).sort(sort_field, sort_direction)
            assets = list(cursor)
            
            # Convert ObjectId to string for each asset
            for asset in assets:
                asset["_id"] = str(asset["_id"])
                
            return assets
            
        except Exception as e:
            logger.error(f"Error finding assets: {str(e)}")
            raise
            
    async def update_asset(self, query: Dict[str, Any], update: Dict[str, Any]) -> bool:
        """
        Update an asset document.
        
        Args:
            query: The query to identify document to update
            update: The update operations to perform
            
        Returns:
            True if update was successful, False otherwise
        """
        try:
            result = self.assets_collection.update_one(query, update)
            return result.modified_count > 0
            
        except Exception as e:
            logger.error(f"Error updating asset: {str(e)}")
            raise
            
    async def update_assets(self, query: Dict[str, Any], update: Dict[str, Any]) -> int:
        """
        Update multiple asset documents.
        
        Args:
            query: The query to identify documents to update
            update: The update operations to perform
            
        Returns:
            Number of documents updated
        """
        try:
            result = self.assets_collection.update_many(query, update)
            return result.modified_count
            
        except Exception as e:
            logger.error(f"Error updating assets: {str(e)}")
            raise
            
    async def delete_asset(self, query: Dict[str, Any]) -> bool:
        """
        Hard delete an asset.
        
        Args:
            query: The query to identify document to delete
            
        Returns:
            True if deletion was successful, False otherwise
        """
        try:
            result = self.assets_collection.delete_one(query)
            return result.deleted_count > 0
            
        except Exception as e:
            logger.error(f"Error deleting asset: {str(e)}")
            raise

    async def delete_assets(self, query: Dict[str, Any]) -> int:
        """
        Hard delete multiple assets matching the query.
        
        Args:
            query: The query to identify documents to delete
            
        Returns:
            Number of documents deleted
        """
        try:
            result = self.assets_collection.delete_many(query)
            return result.deleted_count
            
        except Exception as e:
            logger.error(f"Error deleting assets: {str(e)}")
            raise
