from fastapi import UploadFile
from typing import List, Dict, Any, Optional
from io import StringIO
import json
import pandas as pd
import logging
from dotenv import load_dotenv
from app.services.asset_service import AssetService
from app.services.ipfs_service import IPFSService
from app.services.blockchain_service import BlockchainService
from app.services.transaction_service import TransactionService
from app.services.transaction_state_service import TransactionStateService
from app.utilities.format import get_ipfs_metadata

logger = logging.getLogger(__name__)

class UploadHandler:
    """
    Handler for file upload operations.
    Coordinates the process of uploading files to IPFS, storing CIDs on blockchain,
    and creating/updating asset documents in MongoDB.
    """

    def __init__(
        self, 
        asset_service: AssetService = None,
        ipfs_service: IPFSService = None,
        blockchain_service: BlockchainService = None,
        transaction_service: TransactionService = None,
        transaction_state_service: TransactionStateService = None,
        auth_context: Optional[Dict[str, Any]] = None
    ):
        """
        Initialize with services.
        
        Args:
            asset_service: Service for asset operations
            ipfs_service: Service for IPFS operations
            blockchain_service: Service for blockchain operations
            transaction_service: Service for transaction operations
            transaction_state_service: Service for managing pending transactions
            auth_context: Authentication context for the current request
        """
        self.asset_service = asset_service
        self.ipfs_service = ipfs_service or IPFSService()
        self.blockchain_service = blockchain_service or BlockchainService()
        self.transaction_service = transaction_service
        self.transaction_state_service = transaction_state_service or TransactionStateService()
        self.auth_context = auth_context
        load_dotenv()

    def calculate_batch_ttl(self, asset_count: int) -> int:
        """
        Calculate TTL for batch uploads based on the number of assets.
        
        Formula: 5 minutes base + 1 minute per asset, capped at 60 minutes
        - Small uploads (1-3 assets): 6-8 minutes (reasonable for quick transactions)
        - Medium batches (10-20 assets): 15-25 minutes  
        - Large batches (40-50 assets): 45-55 minutes
        
        Args:
            asset_count: Number of assets in the batch
            
        Returns:
            TTL in seconds
        """
        base_ttl = 300  # 5 minutes base (reduced from 15)
        per_asset_ttl = 60  # 1 minute per asset
        max_ttl = 3600  # 60 minutes maximum (reduced from 90)
        
        calculated_ttl = base_ttl + (asset_count * per_asset_ttl)
        final_ttl = min(calculated_ttl, max_ttl)
        
        logger.info(f"Calculated batch TTL for {asset_count} assets: {final_ttl}s ({final_ttl//60} minutes)")
        return final_ttl

    async def process_metadata(
        self, 
        asset_id: str,
        owner_address: str,
        initiator_address: str,
        critical_metadata: Dict[str, Any],
        non_critical_metadata: Dict[str, Any],
        file_info: Optional[Dict[str, str]] = None
    ) -> Dict[str, Any]:
        """
        Core function to process metadata for an asset.
        
        - Checks if asset exists
        - Determines if critical metadata has changed using CID comparison
        - Handles IPFS/blockchain if needed
        - Updates MongoDB with new version or creates new document
        
        Args:
            asset_id: The asset's unique identifier
            owner_address: The wallet address of the asset owner
            initiator_address: The wallet address of the user initiating the operation
            critical_metadata: Core metadata that will be stored on blockchain
            non_critical_metadata: Additional metadata stored only in MongoDB
            file_info: Optional information about source file
            
        Returns:
            Dict with processing results
        """
        try:
            # Check if asset_id already exists
            existing_doc = None
            was_deleted = False
            try:
                # First check for non-deleted assets
                existing_doc = await self.asset_service.get_asset(asset_id)
                
                # If not found, check if there's a deleted asset with this ID
                if not existing_doc:
                    deleted_doc = await self.asset_service.get_asset_with_deleted(asset_id)
                    if deleted_doc and deleted_doc.get("isDeleted", False):
                        existing_doc = deleted_doc
                        was_deleted = True
            except Exception as e:
                logger.error(f"Error checking for existing document: {str(e)}")
                result = {"asset_id": asset_id, "status": "error", "detail": f"Error checking for existing document: {str(e)}"}
                if file_info:
                    result.update(file_info)
                return result
            
            # Extract IPFS-relevant metadata
            ipfs_metadata = get_ipfs_metadata({
                "asset_id": asset_id,
                "wallet_address": owner_address,  # Use owner address in metadata
                "critical_metadata": critical_metadata
            })
            
            if existing_doc:
                # Document exists, check if critical metadata changed
                existing_ipfs_hash = existing_doc.get("ipfsHash")
                
                # Compute CID for the current metadata
                computed_cid = await self.ipfs_service.compute_cid(ipfs_metadata)
                
                # If CIDs match, then critical metadata has NOT changed
                critical_metadata_changed = computed_cid != existing_ipfs_hash
                
                # Get current ipfsVersion from document or fallback to versionNumber
                current_ipfs_version = existing_doc.get("ipfsVersion", existing_doc.get("versionNumber", 1))
                
                # Force blockchain update if the asset was deleted, even if critical_metadata hasn't changed
                if critical_metadata_changed or was_deleted:
                    # Critical metadata changed or asset was deleted - upload to IPFS and blockchain
                    # 1) Upload to IPFS
                    cid = await self.ipfs_service.store_metadata(ipfs_metadata)
                    
                    # 2) Handle blockchain interaction based on authentication method
                    if self.auth_context and self.auth_context.get("auth_method") == "wallet":
                        # For wallet users, prepare unsigned transaction and return for signing
                        if initiator_address.lower() == owner_address.lower():
                            # Regular update (owner updating their own asset)
                            blockchain_result = await self.blockchain_service.store_hash(cid, asset_id, self.auth_context)
                        else:
                            # Delegate updating on behalf of owner
                            blockchain_result = await self.blockchain_service.store_hash_for(cid, asset_id, owner_address, self.auth_context)
                        
                        if not blockchain_result.get("success"):
                            raise Exception(f"Failed to prepare transaction: {blockchain_result.get('error')}")
                        
                        # Store pending transaction state
                        pending_data = {
                            "asset_id": asset_id,
                            "owner_address": owner_address,
                            "initiator_address": initiator_address,
                            "ipfs_cid": cid,
                            "critical_metadata": critical_metadata,
                            "non_critical_metadata": non_critical_metadata,
                            "action": "updateIPFS" if initiator_address.lower() == owner_address.lower() else "updateIPFSFor",
                            "was_deleted": was_deleted,
                            "transaction": blockchain_result["transaction"],
                            "current_ipfs_version": current_ipfs_version,
                            "file_info": file_info
                        }
                        
                        pending_tx_id = await self.transaction_state_service.store_pending_transaction(
                            user_address=initiator_address,
                            transaction_data=pending_data
                        )
                        
                        # Return transaction for frontend to sign
                        result = {
                            "asset_id": asset_id,
                            "status": "pending_signature",
                            "message": "Transaction prepared for signing",
                            "pending_tx_id": pending_tx_id,
                            "ipfs_cid": cid,
                            "transaction": blockchain_result["transaction"],
                            "estimated_gas": blockchain_result.get("estimated_gas"),
                            "gas_price": blockchain_result.get("gas_price"),
                            "function_name": blockchain_result.get("function_name"),
                            "owner_address": owner_address,
                            "initiator_address": initiator_address,
                            "next_step": "sign_and_broadcast"
                        }
                        
                        if file_info:
                            result.update(file_info)
                        return result
                    
                    else:
                        # For API key users, use existing server-signed logic
                        blockchain_result = None
                        if initiator_address.lower() == owner_address.lower():
                            # Regular update (owner updating their own asset)
                            blockchain_result = await self.blockchain_service.store_hash(cid, asset_id)
                        else:
                            # Admin/delegate updating on behalf of owner
                            blockchain_result = await self.blockchain_service.store_hash_for(cid, asset_id, owner_address)
                        
                        blockchain_tx_hash = blockchain_result.get("tx_hash")
                    
                    # 3) Handle based on whether the asset was deleted
                    if was_deleted:
                        # For deleted assets, create a fresh asset 
                        # Query blockchain for actual version after transaction
                        blockchain_info = await self.blockchain_service.get_ipfs_info(asset_id, owner_address)
                        actual_ipfs_version = blockchain_info.get("ipfs_version", 1)
                        
                        # This will delete all previous versions marked as deleted
                        new_doc_id = await self.asset_service.create_asset(
                            asset_id=asset_id,
                            wallet_address=owner_address,
                            smart_contract_tx_id=blockchain_tx_hash,
                            ipfs_hash=cid,
                            critical_metadata=critical_metadata,
                            non_critical_metadata=non_critical_metadata,
                            ipfs_version=actual_ipfs_version
                        )
                        
                        # Record transaction
                        if self.transaction_service:
                            performed_by = initiator_address if initiator_address.lower() != owner_address.lower() else owner_address
                            
                            await self.transaction_service.record_transaction(
                                asset_id=asset_id,
                                action="RECREATE_DELETED",
                                wallet_address=owner_address,
                                performed_by=performed_by,
                                metadata={
                                    "ipfsHash": cid,
                                    "smartContractTxId": blockchain_tx_hash,
                                    "versionNumber": 1,
                                    "ipfsVersion": 1,
                                    "wasDeleted": True,
                                    "ownerAddress": owner_address
                                }
                            )
                        
                        message = "Asset recreated from deleted state with version reset to 1"
                        
                        result = {
                            "asset_id": asset_id,
                            "status": "success",
                            "message": message,
                            "document_id": new_doc_id,
                            "version": 1,
                            "ipfs_version": 1,
                            "ipfs_cid": cid,
                            "blockchain_tx_hash": blockchain_tx_hash,
                            "owner_address": owner_address,
                            "initiator_address": initiator_address
                        }
                    else:
                        # For non-deleted assets, create a new version
                        # Increment ipfsVersion since critical metadata changed
                        next_ipfs_version = current_ipfs_version + 1
                        
                        version_result = await self.asset_service.create_new_version(
                            asset_id=asset_id,
                            wallet_address=owner_address,
                            smart_contract_tx_id=blockchain_tx_hash,
                            ipfs_hash=cid,
                            critical_metadata=critical_metadata,
                            non_critical_metadata=non_critical_metadata,
                            ipfs_version=next_ipfs_version,
                            performed_by=initiator_address
                        )
                        
                        # Extract results
                        new_doc_id = version_result["document_id"]
                        version_number = version_result["version_number"]
                        ipfs_version = version_result.get("ipfs_version", next_ipfs_version)
                        
                        # Record transaction
                        if self.transaction_service:
                            performed_by = initiator_address if initiator_address.lower() != owner_address.lower() else owner_address
                            
                            tx_action = "VERSION_CREATE"
                            await self.transaction_service.record_transaction(
                                asset_id=asset_id,
                                action=tx_action,
                                wallet_address=owner_address,
                                performed_by=performed_by,
                                metadata={
                                    "ipfsHash": cid,
                                    "smartContractTxId": blockchain_tx_hash,
                                    "versionNumber": version_number,
                                    "ipfsVersion": ipfs_version,
                                    "ownerAddress": owner_address
                                }
                            )
                        
                        message = "New version created with updated critical metadata"
                        
                        result = {
                            "asset_id": asset_id,
                            "status": "success",
                            "message": message,
                            "document_id": new_doc_id,
                            "version": version_number,
                            "ipfs_version": ipfs_version,
                            "ipfs_cid": cid,
                            "blockchain_tx_hash": blockchain_tx_hash,
                            "owner_address": owner_address,
                            "initiator_address": initiator_address
                        }
                    
                    if file_info:
                        result.update(file_info)
                    return result
                else:
                    # Only non-critical metadata changed - just update MongoDB
                    # Reuse existing IPFS hash and blockchain transaction ID
                    existing_tx_hash = existing_doc.get("smartContractTxId")
                    
                    # Create new version in MongoDB for non-deleted asset
                    # Keep ipfsVersion the same since critical metadata hasn't changed
                    version_result = await self.asset_service.create_new_version(
                        asset_id=asset_id,
                        wallet_address=owner_address,
                        smart_contract_tx_id=existing_tx_hash,
                        ipfs_hash=existing_ipfs_hash,
                        critical_metadata=critical_metadata,
                        non_critical_metadata=non_critical_metadata,
                        ipfs_version=current_ipfs_version,
                        performed_by=initiator_address
                    )
                    
                    # Extract results
                    new_doc_id = version_result["document_id"]
                    version_number = version_result["version_number"]
                    ipfs_version = version_result.get("ipfs_version", current_ipfs_version)
                    
                    # Record transaction
                    if self.transaction_service:
                        performed_by = initiator_address if initiator_address.lower() != owner_address.lower() else owner_address
                        
                        await self.transaction_service.record_transaction(
                            asset_id=asset_id,
                            action="UPDATE",
                            wallet_address=owner_address,
                            performed_by=performed_by,
                            metadata={
                                "versionNumber": version_number,
                                "ipfsVersion": ipfs_version,
                                "ownerAddress": owner_address
                            }
                        )
                    
                    result = {
                        "asset_id": asset_id,
                        "status": "success",
                        "message": "New version created with updated non-critical metadata only",
                        "document_id": new_doc_id,
                        "version": version_number,
                        "ipfs_version": ipfs_version,
                        "ipfs_cid": existing_ipfs_hash,
                        "blockchain_tx_hash": existing_tx_hash,
                        "owner_address": owner_address,
                        "initiator_address": initiator_address
                    }
                    if file_info:
                        result.update(file_info)
                    return result
            else:
                # New document - proceed with normal flow
                # 1) Upload to IPFS
                cid = await self.ipfs_service.store_metadata(ipfs_metadata)
                
                # 2) Handle blockchain interaction based on authentication method
                if self.auth_context and self.auth_context.get("auth_method") == "wallet":
                    # For wallet users, prepare unsigned transaction and return for signing
                    if initiator_address.lower() == owner_address.lower():
                        # Regular creation (owner creating their own asset)
                        blockchain_result = await self.blockchain_service.store_hash(cid, asset_id, self.auth_context)
                    else:
                        # Admin/delegate creating on behalf of owner
                        blockchain_result = await self.blockchain_service.store_hash_for(cid, asset_id, owner_address, self.auth_context)
                    
                    if not blockchain_result.get("success"):
                        raise Exception(f"Failed to prepare transaction: {blockchain_result.get('error')}")
                    
                    # Store pending transaction state
                    pending_data = {
                        "asset_id": asset_id,
                        "owner_address": owner_address,
                        "initiator_address": initiator_address,
                        "ipfs_cid": cid,
                        "critical_metadata": critical_metadata,
                        "non_critical_metadata": non_critical_metadata,
                        "action": "updateIPFS" if initiator_address.lower() == owner_address.lower() else "updateIPFSFor",
                        "was_deleted": False,
                        "is_new_document": True,
                        "transaction": blockchain_result["transaction"],
                        "file_info": file_info
                    }
                    
                    pending_tx_id = await self.transaction_state_service.store_pending_transaction(
                        user_address=initiator_address,
                        transaction_data=pending_data
                    )
                    
                    # Return transaction for frontend to sign
                    result = {
                        "asset_id": asset_id,
                        "status": "pending_signature",
                        "message": "Transaction prepared for signing",
                        "pending_tx_id": pending_tx_id,
                        "ipfs_cid": cid,
                        "transaction": blockchain_result["transaction"],
                        "estimated_gas": blockchain_result.get("estimated_gas"),
                        "gas_price": blockchain_result.get("gas_price"),
                        "function_name": blockchain_result.get("function_name"),
                        "owner_address": owner_address,
                        "initiator_address": initiator_address,
                        "next_step": "sign_and_broadcast"
                    }
                    
                    if file_info:
                        result.update(file_info)
                    return result
                
                else:
                    # For API key users, use existing server-signed logic
                    if initiator_address.lower() == owner_address.lower():
                        # Regular creation (owner creating their own asset)
                        blockchain_result = await self.blockchain_service.store_hash(cid, asset_id)
                    else:
                        # Admin/delegate creating on behalf of owner
                        blockchain_result = await self.blockchain_service.store_hash_for(cid, asset_id, owner_address)
                    
                    blockchain_tx_hash = blockchain_result.get("tx_hash")
                
                # 3) Insert into MongoDB
                doc_id = await self.asset_service.create_asset(
                    asset_id=asset_id,
                    wallet_address=owner_address,
                    smart_contract_tx_id=blockchain_tx_hash,
                    ipfs_hash=cid,
                    critical_metadata=critical_metadata,
                    non_critical_metadata=non_critical_metadata,
                    ipfs_version=1
                )
                
                # 4) Record transaction if transaction service is available
                if self.transaction_service:
                    performed_by = initiator_address if initiator_address.lower() != owner_address.lower() else owner_address
                    
                    await self.transaction_service.record_transaction(
                        asset_id=asset_id,
                        action="CREATE",
                        wallet_address=owner_address,
                        performed_by=performed_by,
                        metadata={
                            "ipfsHash": cid,
                            "smartContractTxId": blockchain_tx_hash,
                            "ipfsVersion": 1,
                            "ownerAddress": owner_address
                        }
                    )
                
                result = {
                    "asset_id": asset_id,
                    "status": "success",
                    "message": "Document created",
                    "document_id": doc_id,
                    "version": 1,
                    "ipfs_version": 1,
                    "ipfs_cid": cid,
                    "blockchain_tx_hash": blockchain_tx_hash,
                    "owner_address": owner_address,
                    "initiator_address": initiator_address
                }
                if file_info:
                    result.update(file_info)
                return result
                
        except Exception as e:
            logger.error(f"Error processing metadata for asset {asset_id}: {str(e)}")
            result = {"asset_id": asset_id, "status": "error", "detail": f"Error processing metadata: {str(e)}"}
            if file_info:
                result.update(file_info)
            return result
    
    async def complete_blockchain_upload(
        self,
        pending_tx_id: str,
        blockchain_tx_hash: str,
        initiator_address: str
    ) -> Dict[str, Any]:
        """
        Complete the upload process after blockchain transaction is confirmed.
        
        Args:
            pending_tx_id: ID of the pending transaction
            blockchain_tx_hash: Hash of the confirmed blockchain transaction
            initiator_address: Address of the user who initiated the transaction
            
        Returns:
            Dict with completion results
        """
        try:
            # Get pending transaction data
            pending_data = await self.transaction_state_service.get_pending_transaction(pending_tx_id)
            
            if not pending_data:
                raise Exception(f"Pending transaction {pending_tx_id} not found or expired")
            
            # Verify the initiator
            if pending_data.get("user_address", "").lower() != initiator_address.lower():
                raise Exception("Unauthorized: initiator address mismatch")
            
            # Extract data from pending transaction
            asset_id = pending_data["asset_id"]
            owner_address = pending_data["owner_address"]
            ipfs_cid = pending_data["ipfs_cid"]
            critical_metadata = pending_data["critical_metadata"]
            non_critical_metadata = pending_data["non_critical_metadata"]
            was_deleted = pending_data.get("was_deleted", False)
            is_new_document = pending_data.get("is_new_document", False)
            current_ipfs_version = pending_data.get("current_ipfs_version", 1)
            file_info = pending_data.get("file_info")
            
            # Verify transaction was successful
            tx_verification = await self.blockchain_service.verify_transaction_success(blockchain_tx_hash)
            if not tx_verification.get("success"):
                revert_reason = tx_verification.get("revert_reason", "Unknown reason")
                raise Exception(f"Blockchain transaction failed: {revert_reason} (TX: {blockchain_tx_hash})")
            
            # Process based on the operation type
            if is_new_document:
                # Create new asset document
                doc_id = await self.asset_service.create_asset(
                    asset_id=asset_id,
                    wallet_address=owner_address,
                    smart_contract_tx_id=blockchain_tx_hash,
                    ipfs_hash=ipfs_cid,
                    critical_metadata=critical_metadata,
                    non_critical_metadata=non_critical_metadata,
                    ipfs_version=1
                )
                
                # Record transaction
                if self.transaction_service:
                    performed_by = initiator_address if initiator_address.lower() != owner_address.lower() else owner_address
                    
                    await self.transaction_service.record_transaction(
                        asset_id=asset_id,
                        action="CREATE",
                        wallet_address=owner_address,
                        performed_by=performed_by,
                        metadata={
                            "ipfsHash": ipfs_cid,
                            "smartContractTxId": blockchain_tx_hash,
                            "ipfsVersion": 1,
                            "ownerAddress": owner_address
                        }
                    )
                
                result = {
                    "assetId": asset_id,
                    "status": "success",
                    "message": "Document created successfully",
                    "documentId": doc_id,
                    "version": 1,
                    "ipfsVersion": 1,
                    "ipfsCid": ipfs_cid,
                    "blockchainTxHash": blockchain_tx_hash,
                    "ownerAddress": owner_address,
                    "initiatorAddress": initiator_address
                }
                
            elif was_deleted:
                # Recreate deleted asset (version 1)
                doc_id = await self.asset_service.create_asset(
                    asset_id=asset_id,
                    wallet_address=owner_address,
                    smart_contract_tx_id=blockchain_tx_hash,
                    ipfs_hash=ipfs_cid,
                    critical_metadata=critical_metadata,
                    non_critical_metadata=non_critical_metadata,
                    ipfs_version=1
                )
                
                # Record transaction
                if self.transaction_service:
                    performed_by = initiator_address if initiator_address.lower() != owner_address.lower() else owner_address
                    
                    await self.transaction_service.record_transaction(
                        asset_id=asset_id,
                        action="RECREATE_DELETED",
                        wallet_address=owner_address,
                        performed_by=performed_by,
                        metadata={
                            "ipfsHash": ipfs_cid,
                            "smartContractTxId": blockchain_tx_hash,
                            "versionNumber": 1,
                            "ipfsVersion": 1,
                            "wasDeleted": True,
                            "ownerAddress": owner_address
                        }
                    )
                
                result = {
                    "assetId": asset_id,
                    "status": "success",
                    "message": "Asset recreated from deleted state with version reset to 1",
                    "documentId": doc_id,
                    "version": 1,
                    "ipfsVersion": 1,
                    "ipfsCid": ipfs_cid,
                    "blockchainTxHash": blockchain_tx_hash,
                    "ownerAddress": owner_address,
                    "initiatorAddress": initiator_address
                }
                
            else:
                # Create new version of existing asset
                next_ipfs_version = current_ipfs_version + 1
                
                version_result = await self.asset_service.create_new_version(
                    asset_id=asset_id,
                    wallet_address=owner_address,
                    smart_contract_tx_id=blockchain_tx_hash,
                    ipfs_hash=ipfs_cid,
                    critical_metadata=critical_metadata,
                    non_critical_metadata=non_critical_metadata,
                    ipfs_version=next_ipfs_version,
                    performed_by=initiator_address
                )
                
                # Extract results
                doc_id = version_result["document_id"]
                version_number = version_result["version_number"]
                ipfs_version = version_result.get("ipfs_version", next_ipfs_version)
                
                # Record transaction
                if self.transaction_service:
                    performed_by = initiator_address if initiator_address.lower() != owner_address.lower() else owner_address
                    
                    await self.transaction_service.record_transaction(
                        asset_id=asset_id,
                        action="VERSION_CREATE",
                        wallet_address=owner_address,
                        performed_by=performed_by,
                        metadata={
                            "ipfsHash": ipfs_cid,
                            "smartContractTxId": blockchain_tx_hash,
                            "versionNumber": version_number,
                            "ipfsVersion": ipfs_version,
                            "ownerAddress": owner_address
                        }
                    )
                
                result = {
                    "assetId": asset_id,
                    "status": "success",
                    "message": "New version created with updated critical metadata",
                    "documentId": doc_id,
                    "version": version_number,
                    "ipfsVersion": ipfs_version,
                    "ipfsCid": ipfs_cid,
                    "blockchainTxHash": blockchain_tx_hash,
                    "ownerAddress": owner_address,
                    "initiatorAddress": initiator_address
                }
            
            # Clean up pending transaction
            await self.transaction_state_service.remove_pending_transaction(pending_tx_id)
            
            # Add file info if present
            if file_info:
                result.update(file_info)
            
            logger.info(f"Successfully completed blockchain upload for asset {asset_id}")
            return result
            
        except Exception as e:
            logger.error(f"Error completing blockchain upload: {str(e)}")
            return {
                "assetId": "",
                "status": "error",
                "detail": f"Error completing upload: {str(e)}"
            }

    async def handle_metadata_upload(
        self,
        asset_id: str,
        wallet_address: str,
        critical_metadata: str,
        non_critical_metadata: Optional[str] = None,
        owner_address: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Upload metadata directly (not as a file).
        
        Args:
            asset_id: The asset's unique identifier
            wallet_address: The wallet address of the initiator (person doing the action)
            critical_metadata: JSON string of core metadata
            non_critical_metadata: JSON string of additional metadata
            owner_address: The wallet address of the asset owner (for delegation)
            
        Returns:
            Dict with processing results
        """
        try:
            # Parse JSON strings
            critical_md = json.loads(critical_metadata)
            non_critical_md = json.loads(non_critical_metadata) if non_critical_metadata else {}
            
            # Determine the actual owner address
            # If owner_address is provided (delegation case), use it; otherwise initiator is owner
            actual_owner_address = owner_address if owner_address else wallet_address
            initiator_address = wallet_address
            
            # Process metadata
            return await self.process_metadata(
                asset_id=asset_id,
                owner_address=actual_owner_address,
                initiator_address=initiator_address,
                critical_metadata=critical_md,
                non_critical_metadata=non_critical_md
            )
                
        except json.JSONDecodeError as e:
            logger.error(f"Invalid JSON format: {str(e)}")
            return {"asset_id": asset_id, "status": "error", "detail": f"Invalid JSON format: {str(e)}"}
        except Exception as e:
            logger.error(f"Error processing metadata: {str(e)}")
            return {"asset_id": asset_id, "status": "error", "detail": f"Error processing metadata: {str(e)}"}

    async def handle_json_files(
        self, 
        files: List[UploadFile], 
        wallet_address: str
    ) -> Dict[str, Any]:
        """
        Process JSON files uploaded by the user.
        
        - Each JSON file must have: asset_id, critical_metadata, wallet_address (owner), optional non_critical_metadata
        - Each file represents a single document/asset
        - Duplicate asset_ids are skipped (first occurrence is used)
        
        Args:
            files: List of uploaded JSON files
            wallet_address: The wallet address of the initiator
            
        Returns:
            Dict with processing results for each file
        """
        seen_asset_ids = set()
        results = []
        
        for file_obj in files:
            if not file_obj.filename.lower().endswith(".json"):
                results.append({
                    "filename": file_obj.filename,
                    "status": "error",
                    "detail": "Not a JSON file. Use .json extension."
                })
                continue
                
            try:
                content = await file_obj.read()
                try:
                    data = json.loads(content.decode("utf-8"))
                except Exception as e:
                    results.append({
                        "filename": file_obj.filename,
                        "status": "error",
                        "detail": f"Invalid JSON file: {str(e)}"
                    })
                    continue
                
                # Check required fields
                asset_id = data.get("asset_id")
                critical_metadata = data.get("critical_metadata")
                owner_wallet_address = data.get("wallet_address")
                non_critical_metadata = data.get("non_critical_metadata", {})
                
                if not asset_id or not critical_metadata or not owner_wallet_address:
                    results.append({
                        "filename": file_obj.filename,
                        "status": "error",
                        "detail": "Missing 'asset_id', 'wallet_address' (owner), or 'critical_metadata' in JSON."
                    })
                    continue
                
                # If we have not seen asset_id, proceed; else skip
                if asset_id in seen_asset_ids:
                    results.append({
                        "asset_id": asset_id,
                        "filename": file_obj.filename,
                        "status": "skipped",
                        "detail": "Duplicate asset_id; ignoring subsequent file."
                    })
                    continue
                
                # Mark it as seen
                seen_asset_ids.add(asset_id)
                
                # SECURITY: For API key auth, validate TWO-STEP delegation permissions
                if self.auth_context and self.auth_context.get("auth_method") == "api_key":
                    if owner_wallet_address.lower() != wallet_address.lower():
                        # User is trying to create assets for a different wallet
                        # TWO-STEP VALIDATION:
                        # 1. Target wallet must delegate the API key user (permission layer)
                        # 2. Target wallet must delegate the server wallet (technical layer)
                        server_wallet = self.blockchain_service.get_server_wallet_address()
                        
                        try:
                            # Step 1: Check if target wallet delegated the API key user
                            is_user_delegated = await self.blockchain_service.check_delegation(
                                owner_address=owner_wallet_address,
                                delegate_address=wallet_address
                            )
                            
                            # Step 2: Check if target wallet delegated the server wallet
                            is_server_delegated = await self.blockchain_service.check_delegation(
                                owner_address=owner_wallet_address,
                                delegate_address=server_wallet
                            )
                            
                            # Both delegations are required
                            if not is_user_delegated and not is_server_delegated:
                                results.append({
                                    "filename": file_obj.filename,
                                    "asset_id": asset_id,
                                    "status": "error",
                                    "detail": (
                                        f"Wallet {owner_wallet_address} has not delegated either you ({wallet_address}) "
                                        f"or the server wallet ({server_wallet}). "
                                        f"For API key access, both delegations are required. "
                                        f"Ask {owner_wallet_address} to call: "
                                        f"setDelegate('{wallet_address}', true) AND "
                                        f"setDelegate('{server_wallet}', true)"
                                    )
                                })
                                continue
                            elif not is_user_delegated:
                                results.append({
                                    "filename": file_obj.filename,
                                    "asset_id": asset_id,
                                    "status": "error",
                                    "detail": (
                                        f"Wallet {owner_wallet_address} has not delegated you ({wallet_address}). "
                                        f"Cannot create assets for this wallet via API key. "
                                        f"Ask {owner_wallet_address} to call setDelegate('{wallet_address}', true)"
                                    )
                                })
                                continue
                            elif not is_server_delegated:
                                results.append({
                                    "filename": file_obj.filename,
                                    "asset_id": asset_id,
                                    "status": "error",
                                    "detail": (
                                        f"Wallet {owner_wallet_address} has not delegated the server wallet ({server_wallet}). "
                                        f"Cannot create assets for this wallet via API key. "
                                        f"Ask {owner_wallet_address} to call setDelegate('{server_wallet}', true)"
                                    )
                                })
                                continue
                                
                        except Exception as e:
                            if "has not delegated" in str(e):
                                results.append({
                                    "filename": file_obj.filename,
                                    "asset_id": asset_id,
                                    "status": "error",
                                    "detail": str(e)
                                })
                                continue
                            else:
                                results.append({
                                    "filename": file_obj.filename,
                                    "asset_id": asset_id,
                                    "status": "error",
                                    "detail": f"Unable to verify delegation for {owner_wallet_address}: {str(e)}"
                                })
                                continue
                
                # Process metadata with file info
                # Pass both owner address (from JSON) and initiator address (from route parameter)
                result = await self.process_metadata(
                    asset_id=asset_id,
                    owner_address=owner_wallet_address,
                    initiator_address=wallet_address,
                    critical_metadata=critical_metadata,
                    non_critical_metadata=non_critical_metadata,
                    file_info={"filename": file_obj.filename}
                )
                
                results.append(result)
                    
            except Exception as e:
                results.append({
                    "filename": file_obj.filename,
                    "status": "error",
                    "detail": f"Error processing file: {str(e)}"
                })
        
        return {
            "upload_count": len(results),
            "results": results
        }

    async def _process_batch_background(
        self,
        batch_id: str,
        validated_assets: List[Dict[str, Any]],
        initiator_address: str
    ) -> None:
        """
        Background task to handle IPFS uploads and blockchain preparation.
        Updates progress tracker with real-time status.
        """
        from app.services.progress_service import progress_tracker
        import asyncio
        
        try:
            # Prepare metadata for concurrent upload
            ipfs_metadata_list = []
            for asset_data in validated_assets:
                ipfs_metadata = get_ipfs_metadata({
                    "asset_id": asset_data["asset_id"],
                    "wallet_address": asset_data["owner_address"],
                    "critical_metadata": asset_data["critical_metadata"]
                })
                ipfs_metadata_list.append(ipfs_metadata)
            
            # Define progress callback
            def update_progress(asset_id: str, progress: int, status: str):
                progress_tracker.update_asset_progress(batch_id, asset_id, progress, status)
            
            logger.info(f"Starting background IPFS uploads for batch {batch_id}")
            
            # Upload all assets concurrently
            upload_results = await self.ipfs_service.store_metadata_batch_concurrent(
                ipfs_metadata_list, 
                progress_callback=update_progress,
                max_concurrent=10
            )
            
            # Check for any failed uploads
            failed_uploads = [r for r in upload_results if r["status"] == "error"]
            if failed_uploads:
                for failed in failed_uploads:
                    update_progress(failed["asset_id"], 0, "error")
                logger.error(f"IPFS upload failed for {len(failed_uploads)} assets in batch {batch_id}")
                return
            
            # Combine upload results with original asset data
            ipfs_results = []
            upload_results_by_id = {r["asset_id"]: r for r in upload_results}
            
            for asset_data in validated_assets:
                upload_result = upload_results_by_id[asset_data["asset_id"]]
                ipfs_results.append({
                    "asset_id": asset_data["asset_id"],
                    "cid": upload_result["cid"],
                    "owner_address": asset_data["owner_address"],
                    "critical_metadata": asset_data["critical_metadata"],
                    "non_critical_metadata": asset_data["non_critical_metadata"]
                })
            
            logger.info(f"IPFS uploads completed for batch {batch_id}, preparing blockchain transaction")
            
            # Handle blockchain preparation for wallet auth users
            if self.auth_context and self.auth_context.get("auth_method") == "wallet":
                # Prepare blockchain transaction
                asset_ids = [r["asset_id"] for r in ipfs_results]
                cids = [r["cid"] for r in ipfs_results]
                
                try:
                    blockchain_result = await self.blockchain_service.prepare_batch_transaction(
                        asset_ids=asset_ids,
                        cids=cids,
                        from_address=initiator_address
                    )
                    
                    if not blockchain_result.get("success"):
                        raise Exception(f"Failed to prepare batch transaction: {blockchain_result.get('error')}")
                    
                    # Store pending transaction with blockchain data
                    pending_tx = await self.transaction_state_service.store_pending_transaction(
                        user_address=initiator_address,
                        transaction_data={
                            "operation_type": "BATCH_CREATE",
                            "asset_ids": asset_ids,
                            "metadata": {
                                "ipfs_results": ipfs_results,
                                "asset_count": len(ipfs_results),
                                "initiator_address": initiator_address,
                                "batch_id": batch_id,
                                "blockchain_prepared": True,
                                "transaction": blockchain_result["transaction"],
                                "estimated_gas": blockchain_result.get("estimated_gas"),
                                "gas_price": blockchain_result.get("gas_price"),
                                "function_name": blockchain_result.get("function_name")
                            }
                        },
                        ttl=self.calculate_batch_ttl(len(ipfs_results))
                    )
                    
                    logger.info(f"Blockchain transaction prepared for batch {batch_id}, pending_tx: {pending_tx}")
                    
                    # Update progress tracker with blockchain transaction data
                    progress_tracker.set_blockchain_prepared(
                        batch_id=batch_id,
                        transaction_data={
                            "transaction": blockchain_result["transaction"],
                            "estimated_gas": blockchain_result.get("estimated_gas"),
                            "gas_price": blockchain_result.get("gas_price"),
                            "function_name": blockchain_result.get("function_name"),
                            "status": "pending_signature"
                        },
                        pending_tx_id=pending_tx
                    )
                    
                except Exception as e:
                    logger.error(f"Blockchain preparation failed for batch {batch_id}: {str(e)}")
                    # Mark batch as error in progress tracker
                    for asset_data in validated_assets:
                        update_progress(asset_data["asset_id"], 0, "error")
            else:
                # For API key users, complete the full process immediately
                try:
                    # Extract data for blockchain transaction
                    asset_ids = [r["asset_id"] for r in ipfs_results]
                    cids = [r["cid"] for r in ipfs_results]
                    owner_addresses = [r["owner_address"] for r in ipfs_results]
                    
                    # Execute blockchain transaction
                    blockchain_result = await self.blockchain_service.execute_batch_transaction(
                        asset_ids=asset_ids,
                        cids=cids,
                        owner_addresses=owner_addresses
                    )
                    
                    blockchain_tx_hash = blockchain_result.get("tx_hash")
                    if not blockchain_tx_hash:
                        raise Exception("Blockchain transaction failed - no transaction hash returned")
                    
                    logger.info(f"Blockchain transaction completed for batch {batch_id}: {blockchain_tx_hash}")
                    
                    # Create assets in database and update progress
                    for ipfs_result in ipfs_results:
                        asset_id = ipfs_result["asset_id"]
                        cid = ipfs_result["cid"]
                        owner_address = ipfs_result["owner_address"]
                        critical_metadata = ipfs_result["critical_metadata"]
                        non_critical_metadata = ipfs_result["non_critical_metadata"]
                        
                        try:
                            # Create asset document
                            doc_id = await self.asset_service.create_asset(
                                asset_id=asset_id,
                                wallet_address=owner_address,
                                smart_contract_tx_id=blockchain_tx_hash,
                                ipfs_hash=cid,
                                critical_metadata=critical_metadata,
                                non_critical_metadata=non_critical_metadata,
                                ipfs_version=1
                            )
                            
                            # Record transaction for audit trail
                            if self.transaction_service:
                                await self.transaction_service.record_transaction(
                                    asset_id=asset_id,
                                    action="CREATE",
                                    wallet_address=owner_address,
                                    performed_by=initiator_address,
                                    metadata={
                                        "ipfsHash": cid,
                                        "smartContractTxId": blockchain_tx_hash,
                                        "ipfsVersion": 1,
                                        "ownerAddress": owner_address,
                                        "batchId": batch_id
                                    }
                                )
                            
                            # Update progress tracker with actual IPFS CID
                            progress_tracker.update_asset_progress(
                                batch_id=batch_id,
                                asset_id=asset_id,
                                progress=100,
                                status="completed",
                                ipfs_cid=cid
                            )
                            
                            logger.info(f"Asset {asset_id} created successfully in batch {batch_id}")
                            
                        except Exception as asset_error:
                            logger.error(f"Failed to create asset {asset_id} in batch {batch_id}: {str(asset_error)}")
                            progress_tracker.update_asset_progress(
                                batch_id=batch_id,
                                asset_id=asset_id,
                                progress=0,
                                status="error",
                                error=str(asset_error)
                            )
                    
                    logger.info(f"API key batch upload completed successfully for batch {batch_id}")
                    
                except Exception as batch_error:
                    logger.error(f"API key batch upload failed for batch {batch_id}: {str(batch_error)}")
                    # Mark all assets as error
                    for ipfs_result in ipfs_results:
                        progress_tracker.update_asset_progress(
                            batch_id=batch_id,
                            asset_id=ipfs_result["asset_id"],
                            progress=0,
                            status="error",
                            error=str(batch_error)
                        )
                
        except Exception as e:
            logger.error(f"Background processing failed for batch {batch_id}: {str(e)}")
            # Mark all remaining assets as error
            for asset_data in validated_assets:
                progress_tracker.update_asset_progress(batch_id, asset_data["asset_id"], 0, "error")

    async def process_batch_metadata(
        self,
        assets: List[Dict[str, Any]],
        initiator_address: str
    ) -> Dict[str, Any]:
        """
        Process multiple assets in a batch with single blockchain transaction.
        
        Uses dynamic TTL for auto-completion protection:
        - Formula: 5 minutes base + 1 minute per asset (capped at 60 minutes)
        - Small uploads (1-3 assets): 6-8 minutes protection
        - Large batches (40-50 assets): 45-55 minutes protection
        
        Args:
            assets: List of asset dictionaries with metadata
            initiator_address: The wallet address of the user initiating the batch
            
        Returns:
            Dict with batch processing results
        """
        try:
            # Validate batch size
            if len(assets) > 50:  # Match smart contract limit
                return {
                    "status": "error",
                    "message": "Batch size exceeds maximum of 50 assets",
                    "asset_count": len(assets)
                }
            
            if len(assets) == 0:
                return {
                    "status": "error", 
                    "message": "Must provide at least one asset",
                    "asset_count": 0
                }
            
            # Step 1: Validate all assets and check for conflicts
            validated_assets = []
            for idx, asset in enumerate(assets):
                try:
                    asset_id = asset.get("asset_id")
                    owner_address = asset.get("wallet_address", initiator_address)
                    critical_metadata = asset.get("critical_metadata", {})
                    non_critical_metadata = asset.get("non_critical_metadata", {})
                    
                    # SECURITY: For API key auth, validate TWO-STEP delegation permissions
                    if self.auth_context and self.auth_context.get("auth_method") == "api_key":
                        if owner_address.lower() != initiator_address.lower():
                            # User is trying to create assets for a different wallet
                            # TWO-STEP VALIDATION:
                            # 1. Target wallet must delegate the API key user (permission layer)
                            # 2. Target wallet must delegate the server wallet (technical layer)
                            server_wallet = self.blockchain_service.get_server_wallet_address()
                            
                            try:
                                # Step 1: Check if target wallet delegated the API key user
                                is_user_delegated = await self.blockchain_service.check_delegation(
                                    owner_address=owner_address,
                                    delegate_address=initiator_address
                                )
                                
                                # Step 2: Check if target wallet delegated the server wallet
                                is_server_delegated = await self.blockchain_service.check_delegation(
                                    owner_address=owner_address,
                                    delegate_address=server_wallet
                                )
                                
                                # Both delegations are required
                                if not is_user_delegated and not is_server_delegated:
                                    raise ValueError(
                                        f"Wallet {owner_address} has not delegated either you ({initiator_address}) "
                                        f"or the server wallet ({server_wallet}). "
                                        f"For API key access, both delegations are required. "
                                        f"Ask {owner_address} to call: "
                                        f"setDelegate('{initiator_address}', true) AND "
                                        f"setDelegate('{server_wallet}', true)"
                                    )
                                elif not is_user_delegated:
                                    raise ValueError(
                                        f"Wallet {owner_address} has not delegated you ({initiator_address}). "
                                        f"Cannot create assets for this wallet via API key. "
                                        f"Ask {owner_address} to call setDelegate('{initiator_address}', true)"
                                    )
                                elif not is_server_delegated:
                                    raise ValueError(
                                        f"Wallet {owner_address} has not delegated the server wallet ({server_wallet}). "
                                        f"Cannot create assets for this wallet via API key. "
                                        f"Ask {owner_address} to call setDelegate('{server_wallet}', true)"
                                    )
                                    
                            except Exception as e:
                                if "has not delegated" in str(e):
                                    raise e  # Re-raise our clear error message
                                else:
                                    raise ValueError(f"Unable to verify delegation for {owner_address}: {str(e)}")
                    # Note: For wallet auth, user can specify any address but will own assets themselves
                    
                    if not asset_id:
                        raise ValueError(f"Asset at index {idx} missing asset_id")
                    
                    # Check if asset already exists and is not deleted
                    existing_doc = await self.asset_service.get_asset(
                        asset_id=asset_id
                    )
                    
                    if existing_doc and not existing_doc.get("isDeleted"):
                        raise ValueError(f"Asset {asset_id} already exists")
                    
                    validated_assets.append({
                        "asset_id": asset_id,
                        "owner_address": owner_address,
                        "critical_metadata": critical_metadata,
                        "non_critical_metadata": non_critical_metadata,
                        "index": idx
                    })
                    
                except Exception as e:
                    logger.error(f"Validation error for asset {idx}: {str(e)}")
                    return {
                        "status": "error",
                        "message": f"Validation failed for asset {idx}: {str(e)}",
                        "asset_count": len(assets)
                    }
            
            # Step 2: Setup progress tracking and start background processing
            from app.services.progress_service import progress_tracker
            import uuid
            
            # Generate unique batch ID  
            batch_id = str(uuid.uuid4())
            asset_ids = [asset_data["asset_id"] for asset_data in validated_assets]
            
            # Initialize progress tracking
            progress_tracker.create_batch(batch_id, asset_ids, len(validated_assets))
            
            logger.info(f"Created batch {batch_id} with {len(validated_assets)} assets, starting background processing")
            
            # Start background task for IPFS uploads and blockchain preparation
            import asyncio
            task = asyncio.create_task(
                self._process_batch_background(batch_id, validated_assets, initiator_address)
            )
            
            # Don't await the task - let it run in background
            # Store task reference for potential cleanup (optional)
            # self._background_tasks[batch_id] = task
            
            # Return immediately with batch_id for frontend polling
            if self.auth_context and self.auth_context.get("auth_method") == "wallet":
                return {
                    "status": "pending_signature",
                    "message": f"Sign transaction to create {len(assets)} assets in batch",
                    "asset_count": len(assets),
                    "batch_id": batch_id,
                    "pending_tx_id": f"batch_pending:{batch_id}",  # Placeholder, real one created in background
                    "transaction": None,  # Will be prepared in background
                    "estimated_gas": None,
                    "gas_price": None,
                    "function_name": "batchUpdateIPFS"
                }
            else:
                # API key users - return success, background task will complete the process
                return {
                    "status": "success", 
                    "message": f"Batch upload started for {len(assets)} assets",
                    "asset_count": len(assets),
                    "batch_id": batch_id,
                    "results": [],  # Will be populated as background task completes
                    "successful_count": 0,
                    "failed_count": 0
                }
                
        except Exception as e:
            logger.error(f"Error in batch metadata processing: {str(e)}")
            return {
                "status": "error",
                "message": f"Batch upload failed: {str(e)}",
                "asset_count": len(assets) if assets else 0
            }

    async def complete_batch_blockchain_upload(
        self,
        pending_tx_id: str,
        blockchain_tx_hash: str,
        initiator_address: str
    ) -> Dict[str, Any]:
        """
        Complete batch upload after blockchain transaction is confirmed.
        
        Args:
            pending_tx_id: ID of the pending transaction
            blockchain_tx_hash: Hash of the confirmed blockchain transaction
            initiator_address: Address of the user who initiated the transaction
            
        Returns:
            Dict with completion results
        """
        try:
            # Get pending transaction data
            pending_data = await self.transaction_state_service.get_pending_transaction(pending_tx_id)
            
            if not pending_data:
                raise Exception(f"Pending transaction {pending_tx_id} not found or expired")
            
            # Verify the initiator
            if pending_data.get("user_address", "").lower() != initiator_address.lower():
                raise Exception("Unauthorized: initiator address mismatch")
            
            # Extract data from pending transaction
            ipfs_results = pending_data["metadata"]["ipfs_results"]
            
            # Verify transaction was successful
            tx_verification = await self.blockchain_service.verify_transaction_success(blockchain_tx_hash)
            if not tx_verification.get("success"):
                revert_reason = tx_verification.get("revert_reason", "Unknown reason")
                raise Exception(f"Blockchain transaction failed: {revert_reason} (TX: {blockchain_tx_hash})")
            
            # Create all asset records in database
            results = []
            for asset_data in ipfs_results:
                try:
                    # Query blockchain for actual version after transaction
                    blockchain_info = await self.blockchain_service.get_ipfs_info(
                        asset_data["asset_id"], 
                        asset_data["owner_address"]
                    )
                    actual_ipfs_version = blockchain_info.get("ipfs_version", 1)
                    
                    doc_id = await self.asset_service.create_asset(
                        asset_id=asset_data["asset_id"],
                        wallet_address=asset_data["owner_address"],
                        smart_contract_tx_id=blockchain_tx_hash,
                        ipfs_hash=asset_data["cid"],
                        critical_metadata=asset_data["critical_metadata"],
                        non_critical_metadata=asset_data["non_critical_metadata"],
                        ipfs_version=actual_ipfs_version
                    )
                    
                    # Record transaction
                    if self.transaction_service:
                        performed_by = initiator_address if initiator_address.lower() != asset_data["owner_address"].lower() else asset_data["owner_address"]
                        
                        await self.transaction_service.record_transaction(
                            asset_id=asset_data["asset_id"],
                            action="CREATE",
                            wallet_address=asset_data["owner_address"],
                            performed_by=performed_by,
                            metadata={
                                "ipfsHash": asset_data["cid"],
                                "smartContractTxId": blockchain_tx_hash,
                                "batchUpload": True,
                                "batchId": pending_tx_id,
                                "ipfsVersion": 1,
                                "ownerAddress": asset_data["owner_address"]
                            }
                        )
                    
                    results.append({
                        "asset_id": asset_data["asset_id"],
                        "status": "success",
                        "document_id": doc_id
                    })
                    
                except Exception as e:
                    logger.error(f"Error creating asset {asset_data['asset_id']}: {str(e)}")
                    results.append({
                        "asset_id": asset_data["asset_id"],
                        "status": "error",
                        "detail": str(e)
                    })
            
            # Clean up pending transaction
            await self.transaction_state_service.remove_pending_transaction(pending_tx_id)
            
            # Count successes and failures
            success_count = sum(1 for r in results if r["status"] == "success")
            failed_count = len(results) - success_count
            
            return {
                "status": "success",
                "message": f"Batch upload completed: {success_count}/{len(results)} assets created",
                "asset_count": len(results),
                "results": results,
                "blockchain_tx_hash": blockchain_tx_hash,
                "successful_count": success_count,
                "failed_count": failed_count,
                "batch_id": pending_tx_id
            }
            
        except Exception as e:
            logger.error(f"Error completing batch upload: {str(e)}")
            return {
                "status": "error",
                "message": f"Error completing batch upload: {str(e)}",
                "asset_count": 0
            }

    async def process_csv_upload(
        self,
        files: List[UploadFile],
        wallet_address: str,
        critical_metadata_fields: List[str]
    ) -> Dict[str, Any]:
        """
        Process CSV files uploaded by the user.
        
        - Each row in the CSV is treated as a distinct record with a unique asset_id
        - Must supply 'critical_metadata_fields' to identify which columns are critical
        - Each row must have an 'asset_id' and 'wallet_address' (owner) column
        - Duplicate asset_ids are skipped (first occurrence is used)
        
        Args:
            files: List of uploaded CSV files
            wallet_address: The wallet address of the initiator
            critical_metadata_fields: List of column names to treat as critical metadata
            
        Returns:
            Dict with processing results for each file
        """
        seen_asset_ids = set()
        results = []
        
        # Helper to parse CSV rows into document dictionaries
        def parse_csv(file_content: bytes, critical_fields: List[str]) -> List[Dict[str, Any]]:
            """Parse CSV bytes into a list of asset dictionaries."""
            csv_df = pd.read_csv(StringIO(file_content.decode("utf-8")))

            if "asset_id" not in csv_df.columns:
                raise ValueError("CSV file must contain an 'asset_id' column.")
                
            if "wallet_address" not in csv_df.columns:
                raise ValueError("CSV file must contain a 'wallet_address' (owner) column.")

            # Ensure critical fields exist
            missing = [col for col in critical_fields if col not in csv_df.columns]
            if missing:
                raise ValueError(f"Missing critical columns {missing} in CSV.")

            records = []
            for _, row in csv_df.iterrows():
                row_dict = row.to_dict()

                asset_id = str(row_dict["asset_id"])
                owner_address = str(row_dict["wallet_address"])
                critical_md = {c: row_dict[c] for c in critical_fields}
                # Everything else is non-critical (besides asset_id and wallet_address)
                non_critical_md = {
                    k: v for k, v in row_dict.items()
                    if k not in critical_fields and k != "asset_id" and k != "wallet_address"
                }
                records.append({
                    "asset_id": asset_id,
                    "owner_address": owner_address,
                    "critical_metadata": critical_md,
                    "non_critical_metadata": non_critical_md
                })
            return records
        
        for file_obj in files:
            if not file_obj.filename.lower().endswith(".csv"):
                results.append({
                    "filename": file_obj.filename,
                    "status": "error",
                    "detail": "Not a CSV file. Use .csv extension."
                })
                continue
                
            try:
                content = await file_obj.read()
                try:
                    row_docs = parse_csv(content, critical_metadata_fields)
                except Exception as e:
                    results.append({
                        "filename": file_obj.filename,
                        "status": "error",
                        "detail": f"CSV parse error: {str(e)}"
                    })
                    continue
                
                # Process each row as a separate document
                for row_doc in row_docs:
                    asset_id = row_doc["asset_id"]
                    owner_address = row_doc["owner_address"]
                    
                    # Check for duplicates
                    if asset_id in seen_asset_ids:
                        results.append({
                            "asset_id": asset_id,
                            "filename": file_obj.filename,
                            "status": "skipped",
                            "detail": "Duplicate asset_id found in CSV; ignoring this row."
                        })
                        continue
                    
                    seen_asset_ids.add(asset_id)
                    
                    # SECURITY: For API key auth, validate TWO-STEP delegation permissions
                    if self.auth_context and self.auth_context.get("auth_method") == "api_key":
                        if owner_address.lower() != wallet_address.lower():
                            # User is trying to create assets for a different wallet
                            # TWO-STEP VALIDATION:
                            # 1. Target wallet must delegate the API key user (permission layer)
                            # 2. Target wallet must delegate the server wallet (technical layer)
                            server_wallet = self.blockchain_service.get_server_wallet_address()
                            
                            try:
                                # Step 1: Check if target wallet delegated the API key user
                                is_user_delegated = await self.blockchain_service.check_delegation(
                                    owner_address=owner_address,
                                    delegate_address=wallet_address
                                )
                                
                                # Step 2: Check if target wallet delegated the server wallet
                                is_server_delegated = await self.blockchain_service.check_delegation(
                                    owner_address=owner_address,
                                    delegate_address=server_wallet
                                )
                                
                                # Both delegations are required
                                if not is_user_delegated and not is_server_delegated:
                                    results.append({
                                        "filename": file_obj.filename,
                                        "asset_id": asset_id,
                                        "status": "error",
                                        "detail": (
                                            f"Wallet {owner_address} has not delegated either you ({wallet_address}) "
                                            f"or the server wallet ({server_wallet}). "
                                            f"For API key access, both delegations are required. "
                                            f"Ask {owner_address} to call: "
                                            f"setDelegate('{wallet_address}', true) AND "
                                            f"setDelegate('{server_wallet}', true)"
                                        )
                                    })
                                    continue
                                elif not is_user_delegated:
                                    results.append({
                                        "filename": file_obj.filename,
                                        "asset_id": asset_id,
                                        "status": "error",
                                        "detail": (
                                            f"Wallet {owner_address} has not delegated you ({wallet_address}). "
                                            f"Cannot create assets for this wallet via API key. "
                                            f"Ask {owner_address} to call setDelegate('{wallet_address}', true)"
                                        )
                                    })
                                    continue
                                elif not is_server_delegated:
                                    results.append({
                                        "filename": file_obj.filename,
                                        "asset_id": asset_id,
                                        "status": "error",
                                        "detail": (
                                            f"Wallet {owner_address} has not delegated the server wallet ({server_wallet}). "
                                            f"Cannot create assets for this wallet via API key. "
                                            f"Ask {owner_address} to call setDelegate('{server_wallet}', true)"
                                        )
                                    })
                                    continue
                                    
                            except Exception as e:
                                if "has not delegated" in str(e):
                                    results.append({
                                        "filename": file_obj.filename,
                                        "asset_id": asset_id,
                                        "status": "error",
                                        "detail": str(e)
                                    })
                                    continue
                                else:
                                    results.append({
                                        "filename": file_obj.filename,
                                        "asset_id": asset_id,
                                        "status": "error",
                                        "detail": f"Unable to verify delegation for {owner_address}: {str(e)}"
                                    })
                                    continue
                    
                    # Process metadata with file info
                    result = await self.process_metadata(
                        asset_id=asset_id,
                        owner_address=owner_address,
                        initiator_address=wallet_address,
                        critical_metadata=row_doc["critical_metadata"],
                        non_critical_metadata=row_doc["non_critical_metadata"],
                        file_info={"filename": file_obj.filename}
                    )
                    
                    results.append(result)
                    
            except Exception as e:
                results.append({
                    "filename": file_obj.filename,
                    "status": "error",
                    "detail": f"Error processing file: {str(e)}"
                })
        
        return {
            "upload_count": len(results),
            "results": results
        }

