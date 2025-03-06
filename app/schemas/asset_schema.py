from pydantic import BaseModel, Field
from typing import Dict, Any, Optional
from datetime import datetime

class AssetBase(BaseModel):
    asset_id: str = Field(..., description="Unique identifier of the asset", alias="assetId")
    wallet_address: str = Field(..., description="Ethereum wallet address of the user", alias="walletAddress")

class AssetCreateRequest(AssetBase):
    critical_metadata: Dict[str, Any] = Field(..., 
        description="Metadata fields crucial for integrity, stored in IPFS and Blockchain",
        alias="criticalMetadata"
    )
    non_critical_metadata: Optional[Dict[str, Any]] = Field(
        default_factory=dict, 
        description="Additional metadata not required for integrity checks",
        alias="nonCriticalMetadata"
    )

class AssetUpdateRequest(AssetCreateRequest):
    pass  # Same fields as AssetCreateRequest

class AssetResponse(AssetBase):
    document_id: str = Field(..., description="MongoDB document identifier", alias="_id")
    version_number: int = Field(..., description="Version number of the asset", alias="versionNumber")
    ipfs_hash: str = Field(..., description="CID of the metadata stored in IPFS", alias="ipfsHash")
    smart_contract_tx_id: str = Field(..., description="Transaction hash from the blockchain", alias="smartContractTxId")
    last_updated: datetime = Field(..., description="Timestamp when the asset was last updated", alias="lastUpdated")
    is_current: bool = Field(default=True, description="Indicates whether this version is the current active one", alias="isCurrent")
    is_deleted: bool = Field(default=False, description="Indicates whether this asset is marked as deleted", alias="isDeleted")
    
    # These could be optional since they may not be present in all responses
    previous_version_id: Optional[str] = Field(None, description="ID of the previous version", alias="previousVersionId")
    document_history: Optional[list] = Field(None, description="History of document IDs", alias="documentHistory")

    class Config:
        orm_mode = True  # Allows compatibility with MongoDB returned objects
        allow_population_by_field_name = True  # Allows use of alias field names
        
class AssetVersionInfo(BaseModel):
    document_id: str = Field(..., description="MongoDB document identifier", alias="_id")
    version_number: int = Field(..., description="Version number", alias="versionNumber")
    last_updated: datetime = Field(..., description="When this version was created", alias="lastUpdated")
    is_current: bool = Field(..., description="Whether this is the current version", alias="isCurrent")

    class Config:
        orm_mode = True
        allow_population_by_field_name = True
