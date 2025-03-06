from typing import List, Dict, Any, Optional
from datetime import datetime, timezone
import logging
from app.repositories.transaction_repo import TransactionRepository

logger = logging.getLogger(__name__)

class TransactionService:
    """
    Service for managing transaction history and records.
    Handles retrieving transaction history for assets and wallets,
    and recording new transactions in the system.
    """
    
    def __init__(self, transaction_repository: TransactionRepository):
        """Initialize with the transaction repository."""
        self.transaction_repository = transaction_repository

    async def get_asset_history(
        self, 
        asset_id: str, 
        version: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """
        Get transaction history for a specific asset.
        Optionally filter by version number.
        
        Args:
            asset_id: The unique identifier of the asset
            version: Optional version number to filter transactions
            
        Returns:
            List of transaction records for the asset
        """
        try:
            # Build the query
            query = {"assetId": asset_id}
            
            if version is not None:
                # If version is specified, look for transactions with that version in metadata
                query["$or"] = [
                    {"metadata.versionNumber": version},
                    # For version 1 which might not have metadata
                    {"$and": [{"action": "CREATE"}, {"metadata": {"$exists": False}}]}
                ]
            
            # Get transactions from repository
            transactions = await self.transaction_repository.find_transactions(query)
            
            # Format the transactions for API response
            return self._format_transactions(transactions)
            
        except Exception as e:
            logger.error(f"Error retrieving asset history: {str(e)}")
            raise

    async def get_wallet_history(
        self, 
        wallet_address: str,
        include_all_versions: bool = False,
        asset_service = None
    ) -> List[Dict[str, Any]]:
        """
        Get transaction history for a specific wallet.
        By default, only includes transactions for current versions 
        unless include_all_versions is True.
        
        Args:
            wallet_address: The wallet address to get history for
            include_all_versions: Whether to include all versions or just current ones
            asset_service: Optional asset service for retrieving current documents
            
        Returns:
            List of transaction records for the wallet
        """
        try:
            # First get all current document IDs for this wallet if we're filtering versions
            current_asset_ids = []
            if not include_all_versions and asset_service:
                documents = await asset_service.get_documents_by_wallet(
                    wallet_address, 
                    include_all_versions=False
                )
                current_asset_ids = [doc["assetId"] for doc in documents]
                
                # If no documents found, return empty list
                if not current_asset_ids:
                    return []
            
            # Build query
            query = {"walletAddress": wallet_address}
            
            if not include_all_versions and current_asset_ids:
                query["assetId"] = {"$in": current_asset_ids}
                
            # Get transactions from repository
            transactions = await self.transaction_repository.find_transactions(query)
            
            # Format the transactions for API response
            return self._format_transactions(transactions)
            
        except Exception as e:
            logger.error(f"Error retrieving wallet history: {str(e)}")
            raise

    async def record_transaction(
        self, 
        asset_id: str, 
        action: str, 
        wallet_address: str, 
        metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Record a transaction in the transaction history.
        
        Args:
            asset_id: The ID of the asset involved in the transaction
            action: The type of action (CREATE, UPDATE, VERSION_CREATE, DELETE, etc.)
            wallet_address: The wallet address that initiated the transaction
            metadata: Optional additional metadata about the transaction
            
        Returns:
            The ID of the newly created transaction record
        """
        try:
            # Create transaction data
            transaction_data = {
                "assetId": asset_id,
                "action": action,
                "walletAddress": wallet_address,
                "timestamp": datetime.now(timezone.utc)
            }
            
            if metadata:
                transaction_data["metadata"] = metadata
                
            # Record the transaction
            transaction_id = await self.transaction_repository.insert_transaction(transaction_data)
            
            logger.info(f"Transaction recorded successfully with id: {transaction_id}")
            return transaction_id
            
        except Exception as e:
            logger.error(f"Error recording transaction: {str(e)}")
            raise

    def _format_transactions(self, transactions: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Format transaction records for API response.
        
        Args:
            transactions: List of transaction records from the database
            
        Returns:
            Formatted list of transaction records
        """
        formatted_transactions = []
        
        for tx in transactions:
            # Convert ObjectId to string if needed
            if '_id' in tx:
                tx['_id'] = str(tx['_id'])
                
            # Convert timestamp to ISO format if needed
            if 'timestamp' in tx and isinstance(tx['timestamp'], datetime):
                tx['timestamp'] = tx['timestamp'].isoformat()
                
            formatted_transactions.append(tx)
            
        return formatted_transactions
