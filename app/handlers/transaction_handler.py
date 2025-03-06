from typing import List, Dict, Any, Optional
import logging
from fastapi import HTTPException
from app.services.transaction_service import TransactionService
from app.services.asset_service import AssetService

logger = logging.getLogger(__name__)

class TransactionHandler:
    """
    Handler for transaction-related operations.
    Acts as a bridge between API routes and the transaction service layer.
    """
    
    def __init__(
        self, 
        transaction_service: TransactionService = None,
        asset_service: AssetService = None
    ):
        """
        Initialize with optional service dependencies.
        
        Args:
            transaction_service: Service for transaction operations
            asset_service: Service for asset operations (used for some transaction operations)
        """
        self.transaction_service = transaction_service or TransactionService()
        self.asset_service = asset_service or AssetService()
        
    async def get_asset_history(
        self, 
        asset_id: str, 
        version: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Get transaction history for a specific asset.
        
        Args:
            asset_id: The asset ID to get history for
            version: Optional specific version to filter by
            
        Returns:
            Dict containing transaction history for the asset
            
        Raises:
            HTTPException: If there's an error retrieving the history
        """
        try:
            # First verify the asset exists
            try:
                asset = await self.asset_service.get_asset(asset_id)
                if not asset:
                    raise HTTPException(
                        status_code=404, 
                        detail=f"Asset with ID {asset_id} not found"
                    )
            except Exception as e:
                if isinstance(e, HTTPException):
                    raise e
                logger.error(f"Error verifying asset existence: {str(e)}")
                raise HTTPException(status_code=500, detail=str(e))
            
            # Get the transaction history
            transactions = await self.transaction_service.get_asset_history(
                asset_id=asset_id,
                version=version
            )
            
            # Prepare the response
            return {
                "asset_id": asset_id,
                "version": version,
                "transactions": transactions,
                "transaction_count": len(transactions)
            }
            
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error getting asset history: {str(e)}")
            raise HTTPException(status_code=500, detail=str(e))
            
    async def get_wallet_history(
        self, 
        wallet_address: str,
        include_all_versions: bool = False
    ) -> Dict[str, Any]:
        """
        Get transaction history for a specific wallet.
        
        Args:
            wallet_address: The wallet address to get history for
            include_all_versions: Whether to include all versions or just current ones
            
        Returns:
            Dict containing transaction history for the wallet
            
        Raises:
            HTTPException: If there's an error retrieving the history
        """
        try:
            # Get the transaction history
            transactions = await self.transaction_service.get_wallet_history(
                wallet_address=wallet_address,
                include_all_versions=include_all_versions,
                asset_service=self.asset_service
            )
            
            # Get some summary information
            asset_ids = set()
            actions = {}
            
            for tx in transactions:
                if "assetId" in tx:
                    asset_ids.add(tx["assetId"])
                if "action" in tx:
                    action = tx["action"]
                    actions[action] = actions.get(action, 0) + 1
            
            # Prepare the response
            return {
                "wallet_address": wallet_address,
                "include_all_versions": include_all_versions,
                "transactions": transactions,
                "transaction_count": len(transactions),
                "unique_assets": len(asset_ids),
                "action_summary": actions
            }
            
        except Exception as e:
            logger.error(f"Error getting wallet history: {str(e)}")
            raise HTTPException(status_code=500, detail=str(e))
            
    async def get_transaction_details(self, transaction_id: str) -> Dict[str, Any]:
        """
        Get details for a specific transaction.
        
        Args:
            transaction_id: The ID of the transaction to get details for
            
        Returns:
            Dict containing transaction details
            
        Raises:
            HTTPException: If transaction not found or there's an error
        """
        try:
            # Get the transaction by ID
            transaction = await self.transaction_service.get_transaction_by_id(transaction_id)
            
            if not transaction:
                raise HTTPException(
                    status_code=404,
                    detail=f"Transaction with ID {transaction_id} not found"
                )
                
            # If transaction has an asset ID, get the asset info
            asset = None
            if "assetId" in transaction:
                try:
                    asset = await self.asset_service.get_asset(transaction["assetId"])
                except Exception as asset_error:
                    logger.warning(f"Error getting asset info for transaction: {str(asset_error)}")
            
            # Prepare the response with additional context if available
            response = {
                "transaction": transaction,
                "asset_info": asset if asset else None
            }
            
            return response
            
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error getting transaction details: {str(e)}")
            raise HTTPException(status_code=500, detail=str(e))
            
    async def record_transaction(
        self,
        asset_id: str,
        action: str,
        wallet_address: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Record a new transaction.
        
        Args:
            asset_id: The asset ID involved in the transaction
            action: The type of action (CREATE, UPDATE, VERSION_CREATE, etc.)
            wallet_address: The wallet address performing the action
            metadata: Optional additional transaction metadata
            
        Returns:
            Dict containing information about the recorded transaction
            
        Raises:
            HTTPException: If there's an error recording the transaction
        """
        try:
            # Validate action type
            valid_actions = ["CREATE", "UPDATE", "VERSION_CREATE", "DELETE", "VERIFY"]
            if action not in valid_actions:
                raise HTTPException(
                    status_code=400,
                    detail=f"Invalid action type. Must be one of: {', '.join(valid_actions)}"
                )
            
            # Record the transaction
            transaction_id = await self.transaction_service.record_transaction(
                asset_id=asset_id,
                action=action,
                wallet_address=wallet_address,
                metadata=metadata
            )
            
            # Prepare the response
            return {
                "status": "success",
                "message": f"Transaction recorded successfully",
                "transaction_id": transaction_id,
                "asset_id": asset_id,
                "action": action,
                "wallet_address": wallet_address
            }
            
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error recording transaction: {str(e)}")
            raise HTTPException(status_code=500, detail=str(e))
            
    async def get_transaction_summary(self, wallet_address: str) -> Dict[str, Any]:
        """
        Get a summary of transactions for a wallet address.
        
        Args:
            wallet_address: The wallet address to get summary for
            
        Returns:
            Dict containing transaction summary information
            
        Raises:
            HTTPException: If there's an error getting the summary
        """
        try:
            # Get all transactions for the wallet
            transactions = await self.transaction_service.get_wallet_history(
                wallet_address=wallet_address,
                include_all_versions=True,
                asset_service=self.asset_service
            )
            
            # Process transactions to create a summary
            summary = {
                "total_transactions": len(transactions),
                "actions": {},
                "assets": set(),
                "first_transaction": None,
                "latest_transaction": None
            }
            
            if transactions:
                # Sort by timestamp
                sorted_tx = sorted(
                    transactions, 
                    key=lambda tx: tx.get("timestamp", ""), 
                    reverse=False
                )
                
                # Get first and latest transaction timestamps
                if sorted_tx:
                    summary["first_transaction"] = sorted_tx[0].get("timestamp")
                    summary["latest_transaction"] = sorted_tx[-1].get("timestamp")
                
                # Count actions
                for tx in transactions:
                    action = tx.get("action", "UNKNOWN")
                    summary["actions"][action] = summary["actions"].get(action, 0) + 1
                    
                    if "assetId" in tx:
                        summary["assets"].add(tx["assetId"])
            
            # Convert set to count for the response
            summary["unique_assets"] = len(summary["assets"])
            summary["assets"] = list(summary["assets"])
            
            return {
                "wallet_address": wallet_address,
                "summary": summary
            }
            
        except Exception as e:
            logger.error(f"Error getting transaction summary: {str(e)}")
            raise HTTPException(status_code=500, detail=str(e))
