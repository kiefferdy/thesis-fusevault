from typing import Dict, Any, Optional
import logging
from fastapi import HTTPException

from app.services.asset_service import AssetService
from app.services.blockchain_service import BlockchainService
from app.services.transaction_service import TransactionService

logger = logging.getLogger(__name__)

class TransferHandler:
    """
    Handler for asset transfer operations.
    Manages the transfer of assets between wallets using the blockchain.
    """
    
    def __init__(
        self, 
        asset_service: AssetService,
        blockchain_service: BlockchainService,
        transaction_service: TransactionService = None
    ):
        """
        Initialize with required services.
        
        Args:
            asset_service: Service for asset operations
            blockchain_service: Service for blockchain operations
            transaction_service: Optional service for recording transactions
        """
        self.asset_service = asset_service
        self.blockchain_service = blockchain_service
        self.transaction_service = transaction_service
        
    async def initiate_transfer(
        self,
        asset_id: str,
        current_owner: str,
        new_owner: str,
        notes: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Initiate a transfer of an asset to a new owner.
        
        Args:
            asset_id: The asset ID to transfer
            current_owner: The current owner's wallet address
            new_owner: The new owner's wallet address
            notes: Optional notes about the transfer
            
        Returns:
            Dict containing transfer initiation result
            
        Raises:
            HTTPException: If asset not found, already deleted, or transfer fails
        """
        try:
            # 1. Verify the asset exists in our database
            asset = await self.asset_service.get_asset(asset_id)
            
            if not asset:
                raise HTTPException(
                    status_code=404,
                    detail=f"Asset with ID {asset_id} not found"
                )
                
            # 2. Verify the caller is the current owner
            asset_owner = asset.get("walletAddress", "").lower()
            requester = current_owner.lower()
            
            if asset_owner != requester:
                raise HTTPException(
                    status_code=403,
                    detail=f"Unauthorized: Only the asset owner can initiate a transfer"
                )
                
            # 3. Check if asset is deleted
            if asset.get("isDeleted", False):
                raise HTTPException(
                    status_code=400,
                    detail=f"Cannot transfer deleted asset"
                )
                
            # 4. Check if there's already a pending transfer
            pending_to = await self.blockchain_service.get_pending_transfer(asset_id, current_owner)
            if pending_to and pending_to != "0x0000000000000000000000000000000000000000":
                raise HTTPException(
                    status_code=400,
                    detail=f"Asset already has a pending transfer"
                )
                
            # 5. Initiate the transfer on the blockchain
            try:
                blockchain_result = await self.blockchain_service.initiate_transfer(asset_id, new_owner)
                blockchain_tx_hash = blockchain_result.get("tx_hash")
                
            except Exception as e:
                logger.error(f"Blockchain transfer initiation failed: {str(e)}")
                raise HTTPException(
                    status_code=500,
                    detail=f"Failed to initiate transfer on blockchain: {str(e)}"
                )
                
            # 6. Record the transaction
            transaction_id = None
            if self.transaction_service:
                metadata = {
                    "from": current_owner,
                    "to": new_owner,
                    "transaction_type": "TRANSFER_INITIATED",
                    "blockchain_tx_hash": blockchain_tx_hash,
                    "notes": notes
                }
                
                transaction_id = await self.transaction_service.record_transaction(
                    asset_id=asset_id,
                    action="TRANSFER_INITIATED",
                    wallet_address=current_owner,
                    metadata=metadata
                )
                
            # 7. Return success response
            return {
                "status": "success",
                "message": f"Transfer initiated for asset {asset_id} to {new_owner}",
                "asset_id": asset_id,
                "from": current_owner,
                "to": new_owner,
                "transaction_id": transaction_id,
                "blockchain_tx_hash": blockchain_tx_hash
            }
            
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error initiating transfer: {str(e)}")
            raise HTTPException(status_code=500, detail=f"Error initiating transfer: {str(e)}")
            
    async def accept_transfer(
        self,
        asset_id: str,
        previous_owner: str,
        new_owner: str,
        notes: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Accept a transfer of an asset from the previous owner.
        
        Args:
            asset_id: The asset ID to accept
            previous_owner: The previous owner's wallet address
            new_owner: The new owner's wallet address (the acceptor)
            notes: Optional notes about the transfer
            
        Returns:
            Dict containing transfer acceptance result
            
        Raises:
            HTTPException: If asset not found, no pending transfer exists, or acceptance fails
        """
        try:
            # 1. Verify the asset exists and is owned by the previous owner
            asset = await self.asset_service.get_asset(asset_id)
            
            if not asset:
                raise HTTPException(
                    status_code=404,
                    detail=f"Asset with ID {asset_id} not found"
                )
                
            asset_owner = asset.get("walletAddress", "").lower()
            previous_owner_lower = previous_owner.lower()
            
            if asset_owner != previous_owner_lower:
                raise HTTPException(
                    status_code=400,
                    detail=f"Asset is not owned by the specified previous owner"
                )
                
            # 2. Verify there's a pending transfer to the new owner
            pending_to = await self.blockchain_service.get_pending_transfer(asset_id, previous_owner)
            new_owner_lower = new_owner.lower()
            
            if pending_to.lower() != new_owner_lower:
                raise HTTPException(
                    status_code=400,
                    detail=f"No pending transfer for this asset to this recipient"
                )
                
            # 3. Accept the transfer on the blockchain
            try:
                blockchain_result = await self.blockchain_service.accept_transfer(asset_id, previous_owner)
                blockchain_tx_hash = blockchain_result.get("tx_hash")
                
            except Exception as e:
                logger.error(f"Blockchain transfer acceptance failed: {str(e)}")
                raise HTTPException(
                    status_code=500,
                    detail=f"Failed to accept transfer on blockchain: {str(e)}"
                )
                
            # 4. Update the asset ownership in the database
            # Get the current version metadata
            current_metadata = {
                "critical_metadata": asset.get("criticalMetadata", {}),
                "non_critical_metadata": asset.get("nonCriticalMetadata", {})
            }
            
            # Create a new version with the new owner
            try:
                version_result = await self.asset_service.create_new_version(
                    asset_id=asset_id,
                    wallet_address=new_owner,  # New owner
                    smart_contract_tx_id=blockchain_tx_hash,
                    ipfs_hash=asset.get("ipfsHash"),  # Keep the same IPFS hash
                    critical_metadata=current_metadata["critical_metadata"],
                    non_critical_metadata=current_metadata["non_critical_metadata"]
                )
                
                # Mark the previous version as deleted (transferred)
                await self.asset_service.soft_delete(asset_id, previous_owner)
                
            except Exception as e:
                logger.error(f"Database update for transfer failed: {str(e)}")
                raise HTTPException(
                    status_code=500,
                    detail=f"Transfer accepted on blockchain but database update failed: {str(e)}"
                )
                
            # 5. Record the transaction
            transaction_id = None
            if self.transaction_service:
                metadata = {
                    "from": previous_owner,
                    "to": new_owner,
                    "transaction_type": "TRANSFER_COMPLETED",
                    "blockchain_tx_hash": blockchain_tx_hash,
                    "notes": notes,
                    "new_document_id": version_result["document_id"],
                    "new_version": version_result["version_number"]
                }
                
                transaction_id = await self.transaction_service.record_transaction(
                    asset_id=asset_id,
                    action="TRANSFER_COMPLETED",
                    wallet_address=new_owner,
                    metadata=metadata
                )
                
            # 6. Return success response
            return {
                "status": "success",
                "message": f"Transfer accepted for asset {asset_id} from {previous_owner}",
                "asset_id": asset_id,
                "from": previous_owner,
                "to": new_owner,
                "transaction_id": transaction_id,
                "blockchain_tx_hash": blockchain_tx_hash,
                "document_id": version_result["document_id"],
                "version": version_result["version_number"]
            }
            
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error accepting transfer: {str(e)}")
            raise HTTPException(status_code=500, detail=f"Error accepting transfer: {str(e)}")
            
    async def cancel_transfer(
        self,
        asset_id: str,
        current_owner: str,
        notes: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Cancel a pending transfer.
        
        Args:
            asset_id: The asset ID to cancel transfer for
            current_owner: The current owner's wallet address
            notes: Optional notes about the cancellation
            
        Returns:
            Dict containing transfer cancellation result
            
        Raises:
            HTTPException: If asset not found, no pending transfer exists, or cancellation fails
        """
        try:
            # 1. Verify the asset exists and is owned by the current owner
            asset = await self.asset_service.get_asset(asset_id)
            
            if not asset:
                raise HTTPException(
                    status_code=404,
                    detail=f"Asset with ID {asset_id} not found"
                )
                
            asset_owner = asset.get("walletAddress", "").lower()
            current_owner_lower = current_owner.lower()
            
            if asset_owner != current_owner_lower:
                raise HTTPException(
                    status_code=403,
                    detail=f"Unauthorized: Only the asset owner can cancel a transfer"
                )
                
            # 2. Verify there's a pending transfer
            pending_to = await self.blockchain_service.get_pending_transfer(asset_id, current_owner)
            
            if not pending_to or pending_to == "0x0000000000000000000000000000000000000000":
                raise HTTPException(
                    status_code=400,
                    detail=f"No pending transfer for this asset"
                )
                
            # 3. Cancel the transfer on the blockchain
            try:
                blockchain_result = await self.blockchain_service.cancel_transfer(asset_id)
                blockchain_tx_hash = blockchain_result.get("tx_hash")
                
            except Exception as e:
                logger.error(f"Blockchain transfer cancellation failed: {str(e)}")
                raise HTTPException(
                    status_code=500,
                    detail=f"Failed to cancel transfer on blockchain: {str(e)}"
                )
                
            # 4. Record the transaction
            transaction_id = None
            if self.transaction_service:
                metadata = {
                    "from": current_owner,
                    "to": pending_to,
                    "transaction_type": "TRANSFER_CANCELLED",
                    "blockchain_tx_hash": blockchain_tx_hash,
                    "notes": notes
                }
                
                transaction_id = await self.transaction_service.record_transaction(
                    asset_id=asset_id,
                    action="TRANSFER_CANCELLED",
                    wallet_address=current_owner,
                    metadata=metadata
                )
                
            # 5. Return success response
            return {
                "status": "success",
                "message": f"Transfer cancelled for asset {asset_id}",
                "asset_id": asset_id,
                "from": current_owner,
                "to": pending_to,
                "transaction_id": transaction_id,
                "blockchain_tx_hash": blockchain_tx_hash
            }
            
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error cancelling transfer: {str(e)}")
            raise HTTPException(status_code=500, detail=f"Error cancelling transfer: {str(e)}")
            
    async def get_pending_transfers(
        self,
        wallet_address: str
    ) -> Dict[str, Any]:
        """
        Get all pending transfers for a wallet address.
        
        Args:
            wallet_address: The wallet address to get pending transfers for
            
        Returns:
            Dict containing lists of pending incoming and outgoing transfers
            
        Raises:
            HTTPException: If retrieval fails
        """
        try:
            # This is a more complex operation that would require fetching all assets owned by the user
            # and checking each for pending transfers.
            # For now, we'll implement a simplified version that checks assets owned by this wallet
            
            # 1. Get all assets owned by this wallet
            assets = await self.asset_service.get_documents_by_wallet(wallet_address)
            
            outgoing_transfers = []
            
            # 2. Check each asset for pending transfers
            for asset in assets:
                asset_id = asset.get("assetId")
                
                try:
                    pending_to = await self.blockchain_service.get_pending_transfer(asset_id, wallet_address)
                    
                    if pending_to and pending_to != "0x0000000000000000000000000000000000000000":
                        outgoing_transfers.append({
                            "asset_id": asset_id,
                            "from": wallet_address,
                            "to": pending_to,
                            "asset_info": {
                                "document_id": asset.get("_id"),
                                "version": asset.get("versionNumber"),
                                "critical_metadata": asset.get("criticalMetadata", {})
                            }
                        })
                except Exception as e:
                    logger.error(f"Error checking pending transfers for asset {asset_id}: {str(e)}")
                    # Continue checking other assets
            
            # 3. For incoming transfers, we would need to scan the blockchain events
            # This is a simplification - a real implementation would need to listen to transfer events
            incoming_transfers = []
            
            # 4. Return the results
            return {
                "wallet_address": wallet_address,
                "outgoing_transfers": outgoing_transfers,
                "incoming_transfers": incoming_transfers,
                "total_pending": len(outgoing_transfers) + len(incoming_transfers)
            }
            
        except Exception as e:
            logger.error(f"Error getting pending transfers: {str(e)}")
            raise HTTPException(status_code=500, detail=f"Error getting pending transfers: {str(e)}")
