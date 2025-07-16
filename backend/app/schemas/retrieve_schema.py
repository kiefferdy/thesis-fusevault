from pydantic import BaseModel, Field
from typing import Dict, Any, Optional, List, Protocol, runtime_checkable
import json

class MetadataRetrieveRequest(BaseModel):
    asset_id: str = Field(..., description="The asset's unique identifier", alias="assetId")
    version: Optional[int] = Field(None, description="Specific version to retrieve, defaults to current")
    auto_recover: Optional[bool] = Field(True, description="Whether to automatically recover from tampering")

    model_config = {"populate_by_name": True}

class MetadataVerificationResult(BaseModel):
    # Primary verification result
    verified: bool = Field(..., description="Whether the metadata was verified successfully")
    
    # CID comparison information
    blockchain_cid: str = Field(..., description="CID retrieved from the blockchain", alias="blockchainCid")
    computed_cid: str = Field(..., description="CID computed from the retrieved metadata", alias="computedCid")
    cid_match: bool = Field(..., description="Whether the computed CID matches the blockchain CID", alias="cidMatch")
    
    # Transaction verification
    tx_sender_verified: Optional[bool] = Field(False, description="Whether the transaction sender matches expected server wallet", alias="txSenderVerified")
    
    # Version information from blockchain
    ipfs_version: Optional[int] = Field(None, description="The IPFS version from blockchain", alias="ipfsVersion")
    message: Optional[str] = Field(None, description="Verification message from blockchain")
    is_deleted: Optional[bool] = Field(None, description="Whether the asset is deleted according to blockchain", alias="isDeleted")
    
    # Recovery information
    recovery_needed: bool = Field(..., description="Whether recovery from IPFS was needed", alias="recoveryNeeded")
    recovery_successful: Optional[bool] = Field(None, description="Whether recovery was successful if needed", alias="recoverySuccessful")
    new_version_created: Optional[bool] = Field(None, description="Whether a new version was created after recovery", alias="newVersionCreated")
    
    # Deletion status tampering flag
    deletion_status_tampered: Optional[bool] = Field(None, description="Whether the deletion status was tampered with", alias="deletionStatusTampered")

    model_config = {"populate_by_name": True}

class MetadataRetrieveResponse(BaseModel):
    asset_id: str = Field(..., description="The asset's unique identifier", alias="assetId")
    version: int = Field(..., description="Version number of the retrieved metadata")
    wallet_address: str = Field(..., description="Owner wallet address", alias="walletAddress")
    created_at: Optional[str] = Field(None, description="Asset creation timestamp", alias="createdAt")
    updated_at: Optional[str] = Field(None, description="Asset last update timestamp", alias="updatedAt")
    critical_metadata: Dict[str, Any] = Field(..., description="Core metadata", alias="criticalMetadata")
    non_critical_metadata: Dict[str, Any] = Field(..., description="Additional metadata", alias="nonCriticalMetadata")
    verification: MetadataVerificationResult = Field(..., description="Verification results")
    document_id: str = Field(..., description="MongoDB document ID", alias="documentId")
    ipfs_hash: str = Field(..., description="IPFS content identifier", alias="ipfsHash")
    blockchain_tx_id: str = Field(..., description="Blockchain transaction hash", alias="blockchainTxId")

    model_config = {"populate_by_name": True}


class ProgressMessage(BaseModel):
    """Schema for progress messages sent via Server-Sent Events."""
    step: int = Field(..., description="Current step number (1-based)")
    total_steps: int = Field(..., description="Total number of steps", alias="totalSteps")
    message: str = Field(..., description="Human-readable progress message")
    completed: bool = Field(False, description="Whether the operation is complete")
    error: Optional[str] = Field(None, description="Error message if operation failed")
    
    model_config = {"populate_by_name": True}
    
    def to_sse_data(self) -> str:
        """Convert progress message to Server-Sent Events data format."""
        return f"data: {self.model_dump_json(by_alias=True)}\n\n"


@runtime_checkable
class ProgressCallback(Protocol):
    """Protocol for progress callback functions used in streaming operations."""
    
    async def __call__(self, step: int, total_steps: int, message: str, completed: bool = False, error: Optional[str] = None) -> None:
        """
        Send a progress update.
        
        Args:
            step: Current step number (1-based)
            total_steps: Total number of steps
            message: Human-readable progress message
            completed: Whether the operation is complete
            error: Error message if operation failed
        """
        ...
