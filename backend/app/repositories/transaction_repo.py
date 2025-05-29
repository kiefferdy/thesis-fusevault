from typing import Dict, Any, List, Optional
from pymongo import DESCENDING
import logging

logger = logging.getLogger(__name__)

class TransactionRepository:
    """
    Repository for transaction operations in MongoDB.
    Handles CRUD operations for the transaction collection.
    """
    
    def __init__(self, db_client):
        """
        Initialize with MongoDB client.
        
        Args:
            db_client: The MongoDB client with initialized collections
        """
        self.transaction_collection = db_client.transaction_collection
        
    async def insert_transaction(self, transaction_data: Dict[str, Any]) -> str:
        """
        Insert a new transaction record.
        
        Args:
            transaction_data: Data for the transaction to insert
            
        Returns:
            String ID of the inserted transaction
        """
        try:
            result = self.transaction_collection.insert_one(transaction_data)
            transaction_id = str(result.inserted_id)
            
            logger.info(f"Transaction record inserted with ID: {transaction_id}")
            return transaction_id
            
        except Exception as e:
            logger.error(f"Error inserting transaction: {str(e)}")
            raise
            
    async def find_transactions(self, query: Dict[str, Any], sort_by: str = "timestamp", sort_direction: int = DESCENDING, limit: Optional[int] = None) -> List[Dict[str, Any]]:
        """
        Find transactions matching the query.
        
        Args:
            query: MongoDB query to filter transactions
            sort_by: Field to sort results by (default: timestamp)
            sort_direction: Direction to sort (default: DESCENDING)
            limit: Optional limit on the number of results to return
            
        Returns:
            List of transaction documents
        """
        try:
            # Build cursor
            cursor = self.transaction_collection.find(query).sort(sort_by, sort_direction)
            
            # Apply limit if specified
            if limit is not None and limit > 0:
                cursor = cursor.limit(limit)
            
            # Convert cursor to list
            transactions = list(cursor)
            
            # Log for debugging
            logger.info(f"Found {len(transactions)} transactions with query: {query}")
            
            # Convert ObjectId to string for each transaction
            for tx in transactions:
                if '_id' in tx:
                    tx['_id'] = str(tx['_id'])
                    
            return transactions
            
        except Exception as e:
            logger.error(f"Error finding transactions: {str(e)}")
            # Return empty list instead of raising to prevent frontend crashes
            return []
            
    async def find_transaction(self, query: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Find a single transaction matching the query.
        
        Args:
            query: MongoDB query to filter transaction
            
        Returns:
            Transaction document if found, None otherwise
        """
        try:
            transaction = self.transaction_collection.find_one(query)
            
            if transaction:
                transaction['_id'] = str(transaction['_id'])
                
            return transaction
            
        except Exception as e:
            logger.error(f"Error finding transaction: {str(e)}")
            raise
            
    async def update_transaction(self, query: Dict[str, Any], update: Dict[str, Any]) -> bool:
        """
        Update a transaction.
        
        Args:
            query: Query to identify the transaction to update
            update: The update operations to perform
            
        Returns:
            True if update was successful, False otherwise
        """
        try:
            result = self.transaction_collection.update_one(query, update)
            
            return result.modified_count > 0
            
        except Exception as e:
            logger.error(f"Error updating transaction: {str(e)}")
            raise
            
    async def delete_transaction(self, query: Dict[str, Any]) -> bool:
        """
        Delete a transaction.
        
        Args:
            query: Query to identify the transaction to delete
            
        Returns:
            True if deletion was successful, False otherwise
        """
        try:
            result = self.transaction_collection.delete_one(query)
            
            return result.deleted_count > 0
            
        except Exception as e:
            logger.error(f"Error deleting transaction: {str(e)}")
            raise
