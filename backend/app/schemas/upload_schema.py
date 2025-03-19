from pydantic import BaseModel, Field
from typing import Dict, Any, Optional, List

class MetadataUploadRequest(BaseModel):
    asset_id: str = Field(..., description="The asset's unique identifier", alias="assetId")
    wallet_address: str = Field(..., description="The wallet address of the initiator/owner", alias="walletAddress")
    critical_metadata: Dict[str, Any] = Field(..., description="Core metadata that will be stored on blockchain", alias="criticalMetadata")
    non_critical_metadata: Optional[Dict[str, Any]] = Field({}, description="Additional metadata stored only in MongoDB", alias="nonCriticalMetadata")
    file_info: Optional[Dict[str, str]] = Field(None, description="Optional information about source file", alias="fileInfo")

    class Config:
        populate_by_name = True

class MetadataUploadResponse(BaseModel):
    asset_id: str = Field(..., description="The asset's unique identifier", alias="assetId")
    status: str = Field(..., description="Status of the upload operation")
    message: Optional[str] = Field(None, description="Message describing the result")
    document_id: Optional[str] = Field(None, description="MongoDB document ID", alias="documentId")
    version: Optional[int] = Field(None, description="Version number")
    ipfs_version: Optional[int] = Field(None, description="IPFS version number", alias="ipfsVersion")
    ipfs_cid: Optional[str] = Field(None, description="IPFS content identifier", alias="ipfsCid")
    blockchain_tx_hash: Optional[str] = Field(None, description="Blockchain transaction hash", alias="blockchainTxHash")
    filename: Optional[str] = Field(None, description="Original filename if applicable")
    detail: Optional[str] = Field(None, description="Error details if status is error")
    owner_address: Optional[str] = Field(None, description="The wallet address of the asset owner", alias="ownerAddress")
    initiator_address: Optional[str] = Field(None, description="The wallet address that initiated the operation", alias="initiatorAddress")

    class Config:
        populate_by_name = True

class UploadResultItem(BaseModel):
    asset_id: Optional[str] = Field(None, description="Asset ID if available", alias="assetId")
    filename: Optional[str] = Field(None, description="Original filename")
    status: str = Field(..., description="Status of this item's upload")
    message: Optional[str] = Field(None, description="Message describing the result")
    document_id: Optional[str] = Field(None, description="MongoDB document ID", alias="documentId")
    version: Optional[int] = Field(None, description="Version number")
    ipfs_cid: Optional[str] = Field(None, description="IPFS content identifier", alias="ipfsCid")
    blockchain_tx_hash: Optional[str] = Field(None, description="Blockchain transaction hash", alias="blockchainTxHash")
    detail: Optional[str] = Field(None, description="Error details if status is error")
    owner_address: Optional[str] = Field(None, description="The wallet address of the asset owner", alias="ownerAddress")
    initiator_address: Optional[str] = Field(None, description="The wallet address that initiated the operation", alias="initiatorAddress")

    class Config:
        populate_by_name = True

class CsvUploadResponse(BaseModel):
    upload_count: int = Field(..., description="Number of records processed", alias="uploadCount")
    results: List[Dict[str, Any]] = Field(..., description="Results for each uploaded record")

    class Config:
        populate_by_name = True

class JsonUploadResponse(BaseModel):
    upload_count: int = Field(..., description="Number of records processed", alias="uploadCount")
    results: List[Dict[str, Any]] = Field(..., description="Results for each uploaded record")

    class Config:
        populate_by_name = True
