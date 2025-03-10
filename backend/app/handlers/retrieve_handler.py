from typing import Dict, Any, Optional
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
        version: Optional[int] = None
    ) -> MetadataRetrieveResponse:
        """
        Retrieve and verify metadata for an asset.
        
        Args:
            asset_id: The asset's unique identifier
            version: Optional specific version to retrieve
            
        Returns:
            MetadataRetrieveResponse containing metadata and verification results
            
        Raises:
            HTTPException: If asset not found or retrieval fails
        """
        try:
            # 1. Fetch document from MongoDB
            document = await self.asset_service.get_asset(asset_id, version)
            
            if not document:
                raise HTTPException(status_code=404, detail=f"Asset with ID {asset_id} not found")
                
            # Extract required fields
            doc_id = document["_id"]
            doc_version = document.get("versionNumber", 1)
            wallet_address = document.get("walletAddress")
            blockchain_tx_id = document.get("smartContractTxId")
            ipfs_hash = document.get("ipfsHash")
            critical_metadata = document.get("criticalMetadata", {})
            non_critical_metadata = document.get("nonCriticalMetadata", {})
            
            # 2. Query the blockchain with the tx_id to retrieve the stored hash/CID
            try:
                blockchain_result = await self.blockchain_service.get_hash_from_transaction(blockchain_tx_id)
                blockchain_cid = blockchain_result.get("cid")
                
                if not blockchain_cid:
                    logger.error(f"Could not retrieve CID from blockchain for transaction {blockchain_tx_id}. This is a critical requirement.")
                    # Still fall back to stored hash for verification, but mark verification as failed
                    blockchain_cid = ipfs_hash
                    blockchain_verification = False
                else:
                    blockchain_verification = True
            except Exception as e:
                logger.error(f"Error querying blockchain for transaction {blockchain_tx_id}: {str(e)}")
                # Still fall back to stored hash for verification, but mark verification as failed
                blockchain_cid = ipfs_hash
                blockchain_verification = False
            
            # 3. Compute CID from MongoDB critical metadata
            metadata_for_ipfs = {
                "asset_id": asset_id,
                "wallet_address": wallet_address,
                "critical_metadata": critical_metadata
            }
            computed_cid = await self.ipfs_service.compute_cid(get_ipfs_metadata(metadata_for_ipfs))
            
            # 4. Compare CIDs to check for tampering
            cid_match = computed_cid == blockchain_cid
            
            # Initialize verification result
            verification_result = MetadataVerificationResult(
                verified=cid_match and blockchain_verification,
                cid_match=cid_match,
                blockchain_cid=blockchain_cid,
                computed_cid=computed_cid,
                blockchain_verification=blockchain_verification,
                recovery_needed=not cid_match
            )
            
            # 5. If CIDs don't match, retrieve authentic metadata from IPFS
            new_version_created = False
            
            if not cid_match:
                logger.warning(f"CID mismatch detected for asset {asset_id}. "
                               f"Blockchain CID: {blockchain_cid}, Computed CID: {computed_cid}")
                
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
                        
                        # 6. Create new version with authentic data
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
                                    "recovery_source": "ipfs"
                                }
                            )
                        
                        # Update response data
                        doc_id = new_doc_id
                        doc_version = new_version
                        critical_metadata = authentic_critical_metadata
                        new_version_created = True
                        verification_result.recovery_successful = True
                        
                except Exception as e:
                    logger.error(f"Error recovering metadata from IPFS: {str(e)}")
                    verification_result.recovery_successful = False
            
            # Set new version created flag in verification result
            verification_result.new_version_created = new_version_created
            
            # 7. Prepare response
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
