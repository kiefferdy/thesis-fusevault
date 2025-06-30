from pydantic import BaseModel, Field, validator
from typing import Optional, Dict, Any, List

class DeleteRequest(BaseModel):
    asset_id: str = Field(..., description="The asset's unique identifier", alias="assetId")
    wallet_address: str = Field(..., description="The wallet address of the user performing the deletion", alias="walletAddress")
    reason: Optional[str] = Field(None, description="Optional reason for deletion")
    
    model_config = {"populate_by_name": True}

class DeleteResponse(BaseModel):
    asset_id: str = Field(..., description="The asset's unique identifier", alias="assetId")
    status: str = Field(..., description="Status of the delete operation")
    message: str = Field(..., description="Message describing the deletion result")
    document_id: Optional[str] = Field(None, description="MongoDB document ID", alias="documentId")
    transaction_id: Optional[str] = Field(None, description="Transaction record ID", alias="transactionId")
    
    # New fields for wallet user transaction signing workflow
    pending_tx_id: Optional[str] = Field(None, description="Pending transaction ID for wallet users", alias="pendingTxId")
    transaction: Optional[Dict[str, Any]] = Field(None, description="Unsigned transaction data for wallet users")
    estimated_gas: Optional[int] = Field(None, description="Estimated gas for the transaction", alias="estimatedGas")
    gas_price: Optional[int] = Field(None, description="Gas price for the transaction", alias="gasPrice")
    function_name: Optional[str] = Field(None, description="Smart contract function name", alias="functionName")
    next_step: Optional[str] = Field(None, description="Next step for wallet users", alias="nextStep")
    blockchain_tx_hash: Optional[str] = Field(None, description="Blockchain transaction hash", alias="blockchainTxHash")
    
    model_config = {"populate_by_name": True}

class BatchDeleteRequest(BaseModel):
    asset_ids: List[str] = Field(..., description="List of asset IDs to delete", alias="assetIds")
    wallet_address: str = Field(..., description="The wallet address of the user performing the deletion", alias="walletAddress")
    reason: Optional[str] = Field(None, description="Optional reason for deletion")
    
    model_config = {"populate_by_name": True}

class BatchDeleteResponse(BaseModel):
    status: str = Field(..., description="Overall status of the batch delete operation")
    message: str = Field(..., description="Overall message describing the batch deletion result")
    results: Optional[Dict[str, Any]] = Field(None, description="Results for each asset ID")
    success_count: Optional[int] = Field(None, description="Number of successful deletions", alias="successCount")
    failure_count: Optional[int] = Field(None, description="Number of failed deletions", alias="failureCount")
    
    # For batch prepare operations (when status is 'pending_signature')
    pending_tx_id: Optional[str] = Field(None, description="Pending transaction ID for user signing", alias="pendingTxId")
    batch_id: Optional[str] = Field(None, description="Batch ID for progress tracking", alias="batchId")
    transaction: Optional[Dict[str, Any]] = Field(None, description="Transaction data for MetaMask signing")
    estimated_gas: Optional[int] = Field(None, description="Estimated gas limit", alias="estimatedGas")
    gas_price: Optional[int] = Field(None, description="Gas price in wei", alias="gasPrice")
    function_name: Optional[str] = Field(None, description="Smart contract function name", alias="functionName")
    
    # For completed deletions
    blockchain_tx_hash: Optional[str] = Field(None, description="Blockchain transaction hash", alias="blockchainTxHash")
    asset_count: Optional[int] = Field(None, description="Number of assets in batch", alias="assetCount")
    
    model_config = {"populate_by_name": True}

# New schemas for batch prepare/complete operations
class BatchDeletePrepareRequest(BaseModel):
    """Request model for preparing batch delete operations"""
    asset_ids: List[str] = Field(..., description="List of asset IDs to delete", alias="assetIds")
    wallet_address: str = Field(..., description="Wallet address of the user performing deletion", alias="walletAddress")
    reason: Optional[str] = Field(None, description="Optional reason for deletion")
    
    model_config = {"populate_by_name": True}
    
    @validator('asset_ids')
    def validate_asset_ids(cls, v):
        if not v or len(v) == 0:
            raise ValueError('Must provide at least one asset ID')
        if len(v) > 50:  # Match smart contract limit
            raise ValueError('Batch size cannot exceed 50 assets')
        
        # Check for duplicate asset IDs
        if len(v) != len(set(v)):
            raise ValueError('Duplicate asset IDs found in batch')
        
        # Validate each asset ID is not empty
        for asset_id in v:
            if not asset_id or not asset_id.strip():
                raise ValueError('Asset ID cannot be empty')
        
        return [asset_id.strip() for asset_id in v]

    @validator('wallet_address')
    def validate_wallet_address(cls, v):
        if not v or not v.strip():
            raise ValueError('Wallet address cannot be empty')
        v = v.strip()
        if not v.startswith('0x') or len(v) != 42:
            raise ValueError('Invalid Ethereum address format')
        return v.lower()

class BatchDeleteCompletionRequest(BaseModel):
    """Request model for completing batch delete operations after blockchain confirmation"""
    pending_tx_id: str = Field(..., description="Pending transaction ID", alias="pendingTxId")
    blockchain_tx_hash: str = Field(..., description="Blockchain transaction hash", alias="blockchainTxHash")
    
    model_config = {"populate_by_name": True}
