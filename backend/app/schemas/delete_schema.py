from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, List

class DeleteRequest(BaseModel):
    asset_id: str = Field(..., description="The asset's unique identifier", alias="assetId")
    wallet_address: str = Field(..., description="The wallet address of the user performing the deletion", alias="walletAddress")
    reason: Optional[str] = Field(None, description="Optional reason for deletion")
    
    class Config:
        populate_by_name = True

class DeleteResponse(BaseModel):
    asset_id: str = Field(..., description="The asset's unique identifier", alias="assetId")
    status: str = Field(..., description="Status of the delete operation")
    message: str = Field(..., description="Message describing the deletion result")
    document_id: Optional[str] = Field(None, description="MongoDB document ID", alias="documentId")
    transaction_id: Optional[str] = Field(None, description="Transaction record ID", alias="transactionId")
    
    class Config:
        populate_by_name = True

class UndeleteRequest(BaseModel):
    asset_id: str = Field(..., description="The asset's unique identifier", alias="assetId")
    wallet_address: str = Field(..., description="The wallet address of the user performing the undelete operation", alias="walletAddress")
    
    class Config:
        populate_by_name = True

class UndeleteResponse(BaseModel):
    asset_id: str = Field(..., description="The asset's unique identifier", alias="assetId")
    status: str = Field(..., description="Status of the undelete operation")
    message: str = Field(..., description="Message describing the undelete result")
    document_id: Optional[str] = Field(None, description="MongoDB document ID", alias="documentId")
    transaction_id: Optional[str] = Field(None, description="Transaction record ID", alias="transactionId")
    
    class Config:
        populate_by_name = True

class BatchDeleteRequest(BaseModel):
    asset_ids: List[str] = Field(..., description="List of asset IDs to delete", alias="assetIds")
    wallet_address: str = Field(..., description="The wallet address of the user performing the deletion", alias="walletAddress")
    reason: Optional[str] = Field(None, description="Optional reason for deletion")
    
    class Config:
        populate_by_name = True

class BatchDeleteResponse(BaseModel):
    status: str = Field(..., description="Overall status of the batch delete operation")
    message: str = Field(..., description="Overall message describing the batch deletion result")
    results: Dict[str, Any] = Field(..., description="Results for each asset ID")
    success_count: int = Field(..., description="Number of successful deletions", alias="successCount")
    failure_count: int = Field(..., description="Number of failed deletions", alias="failureCount")
    
    class Config:
        populate_by_name = True
