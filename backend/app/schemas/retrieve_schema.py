from pydantic import BaseModel, Field
from typing import Dict, Any, Optional, List

class MetadataRetrieveRequest(BaseModel):
    asset_id: str = Field(..., description="The asset's unique identifier", alias="assetId")
    version: Optional[int] = Field(None, description="Specific version to retrieve, defaults to current")

    class Config:
        populate_by_name = True

class MetadataVerificationResult(BaseModel):
    verified: bool = Field(..., description="Whether the metadata was verified successfully")
    cid_match: bool = Field(..., description="Whether the computed CID matches the blockchain CID", alias="cidMatch")
    blockchain_cid: str = Field(..., description="CID retrieved from the blockchain", alias="blockchainCid")
    computed_cid: str = Field(..., description="CID computed from the retrieved metadata", alias="computedCid")
    blockchain_digest: Optional[str] = Field(None, description="Digest retrieved from the blockchain", alias="blockchainDigest")
    computed_digest: Optional[str] = Field(None, description="Digest computed from the IPFS hash", alias="computedDigest")
    digest_match: Optional[bool] = Field(None, description="Whether the computed digest matches the blockchain digest", alias="digestMatch")
    blockchain_verification: bool = Field(True, description="Whether blockchain verification was successful", alias="blockchainVerification")
    recovery_needed: bool = Field(..., description="Whether recovery from IPFS was needed", alias="recoveryNeeded")
    recovery_successful: Optional[bool] = Field(None, description="Whether recovery was successful if needed", alias="recoverySuccessful")
    new_version_created: Optional[bool] = Field(None, description="Whether a new version was created after recovery", alias="newVersionCreated")
    original_cid: Optional[str] = Field(None, description="Original CID retrieved from the blockchain transaction", alias="originalCid")

    class Config:
        populate_by_name = True

class MetadataRetrieveResponse(BaseModel):
    asset_id: str = Field(..., description="The asset's unique identifier", alias="assetId")
    version: int = Field(..., description="Version number of the retrieved metadata")
    critical_metadata: Dict[str, Any] = Field(..., description="Core metadata", alias="criticalMetadata")
    non_critical_metadata: Dict[str, Any] = Field(..., description="Additional metadata", alias="nonCriticalMetadata")
    verification: MetadataVerificationResult = Field(..., description="Verification results")
    document_id: str = Field(..., description="MongoDB document ID", alias="documentId")
    ipfs_hash: str = Field(..., description="IPFS content identifier", alias="ipfsHash")
    blockchain_tx_id: str = Field(..., description="Blockchain transaction hash", alias="blockchainTxId")

    class Config:
        populate_by_name = True
