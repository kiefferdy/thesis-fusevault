from typing import Optional
import logging
from fastapi import HTTPException

from app.services.asset_service import AssetService
from app.services.blockchain_service import BlockchainService
from app.services.ipfs_service import IPFSService
from app.services.transaction_service import TransactionService
from app.schemas.retrieve_schema import MetadataRetrieveResponse, MetadataVerificationResult
from app.utilities.format import get_ipfs_metadata

logger = logging.getLogger(__name__)

class RetrieveHandler:
    """
    Handler for metadata retrieval operations.
    Verifies metadata integrity by comparing blockchain CID with computed CID.
    Retrieves authentic metadata from IPFS if tampering is detected.
    """
    
    def __init__(
        self,
        asset_service: AssetService,
        blockchain_service: BlockchainService,
        ipfs_service: IPFSService,
        transaction_service: TransactionService = None
    ):
        """
        Initialize with required services.
        
        Args:
            asset_service: Service for asset operations
            blockchain_service: Service for blockchain operations
            ipfs_service: Service for IPFS operations
            transaction_service: Optional service for recording transactions
        """
        self.asset_service = asset_service
        self.blockchain_service = blockchain_service
        self.ipfs_service = ipfs_service
        self.transaction_service = transaction_service
        
    async def retrieve_metadata(
        self,
        asset_id: str,
        version: Optional[int] = None,
        auto_recover: bool = True
    ) -> MetadataRetrieveResponse:
        """
        Retrieve and verify metadata for an asset.
        
        Args:
            asset_id: The asset's unique identifier
            version: Optional specific version to retrieve
            auto_recover: Whether to automatically recover from tampering (only applies to latest version)
            
        Returns:
            MetadataRetrieveResponse containing metadata and verification results
            
        Raises:
            HTTPException: If asset not found or retrieval fails
        """
        try:
            # 1. First check if the asset exists at all (with any version)
            any_version = await self.asset_service.get_asset_with_deleted(asset_id)
            
            if not any_version:
                raise HTTPException(status_code=404, detail=f"Asset with ID {asset_id} not found")
                
            # 2. Now fetch the specific version requested
            document = await self.asset_service.get_asset(asset_id, version)
            
            if not document:
                if version:
                    raise HTTPException(status_code=404, detail=f"Version {version} of asset {asset_id} not found or is deleted")
                else:
                    # This should not normally happen if any_version exists, unless the asset is deleted
                    raise HTTPException(status_code=404, detail=f"Current version of asset {asset_id} not found or is deleted")
                
            # Extract required fields
            doc_id = document["_id"]
            doc_version = document.get("versionNumber", 1)
            is_latest_version = document.get("isCurrent", False)
            wallet_address = document.get("walletAddress")
            blockchain_tx_id = document.get("smartContractTxId")
            ipfs_hash = document.get("ipfsHash")
            critical_metadata = document.get("criticalMetadata", {})
            non_critical_metadata = document.get("nonCriticalMetadata", {})
            
            # Initialize verification result
            verification_result = MetadataVerificationResult(
                verified=False,
                cid_match=False,
                blockchain_cid="unknown",
                computed_cid="unknown",
                blockchain_verification=False,
                recovery_needed=False
            )
            
            # 3. Query the blockchain with the tx_id to retrieve the stored hash/CID
            blockchain_cid = None
            tx_sender_verified = False
            
            try:
                # Get transaction data from blockchain
                blockchain_result = await self.blockchain_service.get_hash_from_transaction(blockchain_tx_id)
                blockchain_cid = blockchain_result.get("cid")
                
                # Verify transaction sender if possible
                tx_sender = blockchain_result.get("tx_sender")
                server_wallet = self.blockchain_service.wallet_address
                
                if tx_sender and server_wallet:
                    # Convert both addresses to lowercase for case-insensitive comparison
                    tx_sender_lower = tx_sender.lower() if isinstance(tx_sender, str) else None
                    server_wallet_lower = server_wallet.lower() if isinstance(server_wallet, str) else None
                    
                    # Check if transaction sender matches server wallet address
                    tx_sender_verified = (tx_sender_lower and server_wallet_lower and 
                                        tx_sender_lower == server_wallet_lower)
                    
                    if not tx_sender_verified:
                        logger.warning(f"Transaction sender verification failed for {asset_id}. "
                                      f"Expected: {server_wallet_lower}, Found: {tx_sender_lower}")
                else:
                    tx_sender_verified = False
                    logger.warning(f"Transaction sender verification failed - missing data. " 
                                  f"tx_sender: {tx_sender}, server_wallet: {server_wallet}")
                
                if not blockchain_cid:
                    logger.error(f"Could not retrieve CID from blockchain for transaction {blockchain_tx_id}. This is a critical requirement.")
                    # Use a marker value that will cause verification to fail
                    blockchain_cid = "BLOCKCHAIN_RETRIEVAL_FAILED"
                
            except Exception as e:
                logger.error(f"Error querying blockchain for transaction {blockchain_tx_id}: {str(e)}")
                blockchain_cid = "BLOCKCHAIN_RETRIEVAL_FAILED"
            
            # 4. Compute CID from MongoDB critical metadata
            metadata_for_ipfs = {
                "asset_id": asset_id,
                "wallet_address": wallet_address,
                "critical_metadata": critical_metadata
            }
            computed_cid = await self.ipfs_service.compute_cid(get_ipfs_metadata(metadata_for_ipfs))
            
            # 5. Compare CIDs to check for tampering
            cid_match = computed_cid == blockchain_cid
            
            # Update verification result
            verification_result.blockchain_cid = blockchain_cid
            verification_result.computed_cid = computed_cid
            verification_result.cid_match = cid_match
            verification_result.tx_sender_verified = tx_sender_verified
            
            # Final verification result - include both CID match and transaction sender verification
            verification_result.verified = cid_match and tx_sender_verified
            verification_result.recovery_needed = not (cid_match and tx_sender_verified)
            
            # 6. If CIDs don't match or tx sender verification fails, retrieve authentic metadata from IPFS
            # Only if auto_recover is True AND this is the latest version
            new_version_created = False
            
            if verification_result.recovery_needed:
                logger.warning(f"Verification failed for asset {asset_id}. "
                            f"CID match: {cid_match}, TX sender verified: {tx_sender_verified}")
            
            if verification_result.recovery_needed and auto_recover and is_latest_version:
                try:
                    # Retrieve authentic metadata from IPFS
                    try:
                        authentic_metadata = await self.ipfs_service.retrieve_metadata(blockchain_cid)
                    except Exception as ipfs_error:
                        logger.error(f"Failed to retrieve metadata from IPFS: {str(ipfs_error)}")
                        raise ipfs_error
                    
                    # Ensure we have the required fields
                    if not authentic_metadata or "critical_metadata" not in authentic_metadata:
                        logger.error(f"Failed to retrieve valid metadata from IPFS for CID {blockchain_cid}")
                        verification_result.recovery_successful = False
                    else:
                        # Extract authentic critical metadata
                        authentic_critical_metadata = authentic_metadata.get("critical_metadata", {})
                        
                        # 7. Create new version with authentic data
                        new_doc_id = await self.asset_service.create_new_version(
                            asset_id=asset_id,
                            wallet_address=wallet_address,
                            smart_contract_tx_id=blockchain_tx_id,
                            ipfs_hash=blockchain_cid,
                            critical_metadata=authentic_critical_metadata,
                            non_critical_metadata=non_critical_metadata
                        )
                        
                        # Get the new document to get its version number
                        new_doc = await self.asset_service.get_asset(asset_id)
                        new_version = new_doc.get("versionNumber", doc_version + 1)
                        
                        # Record transaction if transaction service is available
                        if self.transaction_service:
                            await self.transaction_service.record_transaction(
                                asset_id=asset_id,
                                action="INTEGRITY_RECOVERY",
                                wallet_address=wallet_address,
                                metadata={
                                    "previous_doc_id": doc_id,
                                    "new_doc_id": new_doc_id,
                                    "previous_version": doc_version,
                                    "new_version": new_version,
                                    "blockchain_cid": blockchain_cid,
                                    "computed_cid": computed_cid,
                                    "recovery_source": "ipfs",
                                    "tx_sender_verified": tx_sender_verified,
                                    "auto_recover": auto_recover
                                }
                            )
                        
                        # Update response data
                        doc_id = new_doc_id["document_id"]
                        doc_version = new_version
                        critical_metadata = authentic_critical_metadata
                        new_version_created = True
                        verification_result.recovery_successful = True
                        
                except Exception as e:
                    logger.error(f"Error recovering metadata from IPFS: {str(e)}")
                    verification_result.recovery_successful = False
            
            # Set new version created flag in verification result
            verification_result.new_version_created = new_version_created
            
            # 8. Prepare response
            return MetadataRetrieveResponse(
                asset_id=asset_id,
                version=doc_version,
                critical_metadata=critical_metadata,
                non_critical_metadata=non_critical_metadata,
                verification=verification_result,
                document_id=doc_id,
                ipfs_hash=blockchain_cid,
                blockchain_tx_id=blockchain_tx_id
            )
            
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error retrieving metadata: {str(e)}")
            raise HTTPException(status_code=500, detail=f"Error retrieving metadata: {str(e)}")
