from typing import Dict, Any, Optional
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
        transaction_service: TransactionService,
        asset_service: AssetService
    ):
        """
        Initialize with required services.
        
        Args:
            transaction_service: Service for transaction operations
            asset_service: Service for asset operations
        """
        self.transaction_service = transaction_service
        self.asset_service = asset_service
        
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
        include_all_versions: bool = False,
        limit: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Get transaction history for a specific wallet.
        
        Args:
            wallet_address: The wallet address to get history for
            include_all_versions: Whether to include all versions or just current ones
            limit: Optional limit on the number of transactions to return
            
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
            
            # Apply limit if specified
            if limit is not None and limit > 0:
                transactions = transactions[:limit]
            
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
                "status": "success",
                "wallet_address": wallet_address,
                "include_all_versions": include_all_versions,
                "transactions": transactions,
                "count": len(transactions),
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
            return {
                "transaction": transaction,
                "asset_info": asset if asset else None
            }
            
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
        performed_by: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Record a new transaction.
        
        Args:
            asset_id: The asset ID involved in the transaction
            action: The type of action (CREATE, UPDATE, VERSION_CREATE, etc.)
            wallet_address: The wallet address that owns the asset
            performed_by: Wallet address that actually performed the action (for delegation)
            metadata: Optional additional transaction metadata
            
        Returns:
            Dict containing information about the recorded transaction
            
        Raises:
            HTTPException: If there's an error recording the transaction
        """
        try:
            # Record the transaction
            transaction_id = await self.transaction_service.record_transaction(
                asset_id=asset_id,
                action=action,
                wallet_address=wallet_address,
                performed_by=performed_by,
                metadata=metadata
            )
            
            # Prepare the response
            return {
                "status": "success",
                "message": f"Transaction recorded successfully",
                "transaction_id": transaction_id,
                "asset_id": asset_id,
                "action": action,
                "wallet_address": wallet_address,
                "performed_by": performed_by
            }
            
        except ValueError as e:
            # This catches the validation error for invalid action types
            raise HTTPException(status_code=400, detail=str(e))
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
            # Get the transaction summary
            summary = await self.transaction_service.get_transaction_summary(wallet_address)
            
            return {
                "status": "success",
                "wallet_address": wallet_address,
                **summary  # Spread the summary fields directly
            }
            
        except Exception as e:
            logger.error(f"Error getting transaction summary: {str(e)}")
            # Instead of an error, return an empty summary
            return {
                "status": "success",
                "wallet_address": wallet_address,
                "total_transactions": 0,
                "unique_assets": 0,
                "total_asset_size": 0,
                "actions": {},
                "asset_types": {}
            }
