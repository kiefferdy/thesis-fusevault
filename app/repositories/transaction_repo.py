from typing import Dict, Any, List, Optional
from datetime import datetime, timezone
from pymongo import DESCENDING
import logging
from bson import ObjectId

logger = logging.getLogger(__name__)

class TransactionRepository:
    """
    Repository for transaction operations in MongoDB.
    Handles saving, retrieving, and querying transaction records.
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
            # Ensure timestamp is set if not provided
            if 'timestamp' not in transaction_data:
                transaction_data['timestamp'] = datetime.now(timezone.utc)
                
            # Insert the document
            result = self.transaction_collection.insert_one(transaction_data)
            transaction_id = str(result.inserted_id)
            
            logger.info(f"Transaction record inserted with ID: {transaction_id}")
            return transaction_id
            
        except Exception as e:
            logger.error(f"Error inserting transaction: {str(e)}")
            raise
            
    async def find_transactions(self, query: Dict[str, Any], sort_by: str = "timestamp") -> List[Dict[str, Any]]:
        """
        Find transactions matching the query.
        
        Args:
            query: MongoDB query to filter transactions
            sort_by: Field to sort results by (default: timestamp)
            
        Returns:
            List of transaction documents
        """
        try:
            # Find matching transactions, sorted by timestamp (newest first)
            cursor = self.transaction_collection.find(query).sort(sort_by, DESCENDING)
            
            # Convert cursor to list
            transactions = list(cursor)
            
            # Convert ObjectId to string for each transaction
            for tx in transactions:
                if '_id' in tx:
                    tx['_id'] = str(tx['_id'])
                    
            return transactions
            
        except Exception as e:
            logger.error(f"Error finding transactions: {str(e)}")
            raise
            
    async def get_transaction_by_id(self, transaction_id: str) -> Optional[Dict[str, Any]]:
        """
        Get a transaction by its ID.
        
        Args:
            transaction_id: The ID of the transaction to retrieve
            
        Returns:
            Transaction document if found, None otherwise
        """
        try:
            # Find the transaction by ID
            transaction = self.transaction_collection.find_one({"_id": ObjectId(transaction_id)})
            
            # Convert ObjectId to string if transaction found
            if transaction:
                transaction['_id'] = str(transaction['_id'])
                
            return transaction
            
        except Exception as e:
            logger.error(f"Error getting transaction by ID: {str(e)}")
            raise
            
    async def get_asset_transactions(self, asset_id: str) -> List[Dict[str, Any]]:
        """
        Get all transactions for a specific asset.
        
        Args:
            asset_id: The ID of the asset
            
        Returns:
            List of transaction documents for the asset
        """
        try:
            return await self.find_transactions({"assetId": asset_id})
            
        except Exception as e:
            logger.error(f"Error getting asset transactions: {str(e)}")
            raise
            
    async def get_wallet_transactions(self, wallet_address: str) -> List[Dict[str, Any]]:
        """
        Get all transactions for a specific wallet.
        
        Args:
            wallet_address: The wallet address
            
        Returns:
            List of transaction documents for the wallet
        """
        try:
            return await self.find_transactions({"walletAddress": wallet_address})
            
        except Exception as e:
            logger.error(f"Error getting wallet transactions: {str(e)}")
            raise
