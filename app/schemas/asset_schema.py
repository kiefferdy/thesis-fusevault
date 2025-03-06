from pydantic import BaseModel, Field
from typing import Dict, Any, Optional
from datetime import datetime

class AssetBase(BaseModel):
    asset_id: str = Field(..., description="Unique identifier of the asset")
    wallet_address: str = Field(..., description="Ethereum wallet address of the user")

class AssetCreateRequest(AssetBase):
    critical_metadata: Dict[str, Any] = Field(..., description="Metadata fields crucial for integrity, stored in IPFS and Blockchain")
    non_critical_metadata: Optional[Dict[str, Any]] = Field(default_factory=dict, description="Additional metadata not required for integrity checks")

class AssetUpdateRequest(AssetCreateRequest):
    critical_metadata: Dict[str, Any] = Field(..., description="Metadata fields crucial for integrity, stored in IPFS and Blockchain")
    non_critical_metadata: Optional[Dict[str, Any]] = Field(default_factory=dict, description="Additional metadata not required for integrity checks")

class AssetResponse(AssetBase):
    document_id: str = Field(..., description="MongoDB document identifier")
    version_number: int = Field(..., description="Version number of the asset")
    ipfs_cid: str = Field(..., description="CID of the metadata stored in IPFS")
    blockchain_tx_hash: str = Field(..., description="Transaction hash from the blockchain")
    last_updated: datetime = Field(..., description="Timestamp when the asset was last updated")
    is_current: bool = Field(default=True, description="Indicates whether this version is the current active one")
    is_deleted: bool = Field(default=False, description="Indicates whether this asset is marked as deleted")

    class Config:
        orm_mode = True  # Allows compatibility with MongoDB returned objects
