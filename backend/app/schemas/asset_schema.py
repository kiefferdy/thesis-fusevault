from pydantic import BaseModel, Field
from typing import Dict, Any, Optional, List
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

class AssetUpdateRequest(BaseModel):
    critical_metadata: Optional[Dict[str, Any]] = Field(
        None,
        description="Metadata fields crucial for integrity, stored in IPFS and Blockchain",
        alias="criticalMetadata"
    )
    non_critical_metadata: Optional[Dict[str, Any]] = Field(
        None, 
        description="Additional metadata not required for integrity checks",
        alias="nonCriticalMetadata"
    )

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
    document_history: Optional[List] = Field(None, description="History of document IDs", alias="documentHistory")

    model_config = {"from_attributes": True, "populate_by_name": True}
        
class AssetVersionInfo(BaseModel):
    document_id: str = Field(..., description="MongoDB document identifier", alias="_id")
    version_number: int = Field(..., description="Version number", alias="versionNumber")
    last_updated: datetime = Field(..., description="When this version was created", alias="lastUpdated")
    is_current: bool = Field(..., description="Whether this is the current version", alias="isCurrent")

    model_config = {"from_attributes": True, "populate_by_name": True}

class AssetHistoryResponse(BaseModel):
    asset_id: str = Field(..., description="Asset ID", alias="assetId")
    version: Optional[int] = Field(None, description="Version number if filtered")
    transactions: List[Dict[str, Any]] = Field(..., description="List of transactions for this asset")
    transaction_count: int = Field(..., description="Number of transactions")

    model_config = {"from_attributes": True, "populate_by_name": True}
        
class AssetListResponse(BaseModel):
    """Response schema for listing assets."""
    status: str = Field(..., description="Status of the request")
    assets: List[Dict[str, Any]] = Field(..., description="List of assets")

    model_config = {"from_attributes": True, "populate_by_name": True}
