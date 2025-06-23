from pydantic import BaseModel, Field, validator
from typing import Dict, Any, Optional, List

class MetadataUploadRequest(BaseModel):
    asset_id: str = Field(..., description="The asset's unique identifier", alias="assetId")
    wallet_address: str = Field(..., description="The wallet address of the initiator/owner", alias="walletAddress")
    critical_metadata: Dict[str, Any] = Field(..., description="Core metadata that will be stored on blockchain", alias="criticalMetadata")
    non_critical_metadata: Optional[Dict[str, Any]] = Field({}, description="Additional metadata stored only in MongoDB", alias="nonCriticalMetadata")
    file_info: Optional[Dict[str, str]] = Field(None, description="Optional information about source file", alias="fileInfo")

    model_config = {"populate_by_name": True}

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
    
    # Fields for pending transactions (when status is 'pending_signature')
    pending_tx_id: Optional[str] = Field(None, description="Pending transaction ID for user signing", alias="pendingTxId")
    transaction: Optional[Dict[str, Any]] = Field(None, description="Transaction data for MetaMask signing")
    estimated_gas: Optional[int] = Field(None, description="Estimated gas limit", alias="estimatedGas")
    gas_price: Optional[int] = Field(None, description="Gas price in wei", alias="gasPrice")
    function_name: Optional[str] = Field(None, description="Smart contract function name", alias="functionName")
    next_step: Optional[str] = Field(None, description="Next step in the process", alias="nextStep")

    model_config = {"populate_by_name": True}

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

    model_config = {"populate_by_name": True}

class CsvUploadResponse(BaseModel):
    upload_count: int = Field(..., description="Number of records processed", alias="uploadCount")
    results: List[Dict[str, Any]] = Field(..., description="Results for each uploaded record")

    model_config = {"populate_by_name": True}

class JsonUploadResponse(BaseModel):
    upload_count: int = Field(..., description="Number of records processed", alias="uploadCount")
    results: List[Dict[str, Any]] = Field(..., description="Results for each uploaded record")

    model_config = {"populate_by_name": True}

# Batch Upload Schemas
class BatchAssetItem(BaseModel):
    """Individual asset item for batch upload"""
    asset_id: str = Field(..., description="The asset's unique identifier", alias="assetId")
    wallet_address: str = Field(..., description="The wallet address of the asset owner", alias="walletAddress")
    critical_metadata: Dict[str, Any] = Field(..., description="Core metadata that will be stored on blockchain", alias="criticalMetadata")
    non_critical_metadata: Optional[Dict[str, Any]] = Field({}, description="Additional metadata stored only in MongoDB", alias="nonCriticalMetadata")

    model_config = {"populate_by_name": True}

    @validator('asset_id')
    def validate_asset_id(cls, v):
        if not v or not v.strip():
            raise ValueError('Asset ID cannot be empty')
        return v.strip()

    @validator('wallet_address')
    def validate_wallet_address(cls, v):
        if not v or not v.strip():
            raise ValueError('Wallet address cannot be empty')
        # Basic Ethereum address validation
        v = v.strip()
        if not v.startswith('0x') or len(v) != 42:
            raise ValueError('Invalid Ethereum address format')
        return v.lower()

class BatchUploadRequest(BaseModel):
    """Request model for batch uploads"""
    assets: List[BatchAssetItem] = Field(..., description="List of assets to upload")
    wallet_address: str = Field(..., description="Wallet address of the uploader/initiator", alias="walletAddress")
    
    model_config = {"populate_by_name": True}

    @validator('assets')
    def validate_assets(cls, v):
        if not v or len(v) == 0:
            raise ValueError('Must provide at least one asset')
        if len(v) > 50:  # Match smart contract limit
            raise ValueError('Batch size cannot exceed 50 assets')
        
        # Check for duplicate asset IDs
        asset_ids = [asset.asset_id for asset in v]
        if len(asset_ids) != len(set(asset_ids)):
            raise ValueError('Duplicate asset IDs found in batch')
        
        return v

    @validator('wallet_address')
    def validate_initiator_wallet_address(cls, v):
        if not v or not v.strip():
            raise ValueError('Wallet address cannot be empty')
        v = v.strip()
        if not v.startswith('0x') or len(v) != 42:
            raise ValueError('Invalid Ethereum address format')
        return v.lower()

class BatchUploadResponse(BaseModel):
    """Response model for batch uploads"""
    status: str = Field(..., description="Status of the batch upload")
    message: str = Field(..., description="Message describing the result")
    asset_count: int = Field(..., description="Number of assets in batch", alias="assetCount")
    
    # For pending transactions (when status is 'pending_signature')
    pending_tx_id: Optional[str] = Field(None, description="Pending transaction ID for user signing", alias="pendingTxId")
    transaction: Optional[Dict[str, Any]] = Field(None, description="Transaction data for MetaMask signing")
    estimated_gas: Optional[int] = Field(None, description="Estimated gas limit", alias="estimatedGas")
    gas_price: Optional[int] = Field(None, description="Gas price in wei", alias="gasPrice")
    function_name: Optional[str] = Field(None, description="Smart contract function name", alias="functionName")
    
    # For completed uploads
    results: Optional[List[Dict[str, Any]]] = Field(None, description="Results for each asset")
    blockchain_tx_hash: Optional[str] = Field(None, description="Blockchain transaction hash", alias="blockchainTxHash")
    
    # Summary information
    successful_count: Optional[int] = Field(None, description="Number of successfully processed assets", alias="successfulCount")
    failed_count: Optional[int] = Field(None, description="Number of failed assets", alias="failedCount")
    
    model_config = {"populate_by_name": True}

class BatchCompletionRequest(BaseModel):
    """Request model for completing batch uploads after blockchain confirmation"""
    pending_tx_id: str = Field(..., description="Pending transaction ID", alias="pendingTxId")
    blockchain_tx_hash: str = Field(..., description="Blockchain transaction hash", alias="blockchainTxHash")
    
    model_config = {"populate_by_name": True}

    @validator('pending_tx_id')
    def validate_pending_tx_id(cls, v):
        if not v or not v.strip():
            raise ValueError('Pending transaction ID cannot be empty')
        return v.strip()

    @validator('blockchain_tx_hash')
    def validate_blockchain_tx_hash(cls, v):
        if not v or not v.strip():
            raise ValueError('Blockchain transaction hash cannot be empty')
        v = v.strip()
        if not v.startswith('0x') or len(v) != 66:
            raise ValueError('Invalid transaction hash format')
        return v.lower()
