from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, List

class TransferInitiateRequest(BaseModel):
    asset_id: str = Field(..., description="The asset's unique identifier", alias="assetId")
    current_owner: str = Field(..., description="The current owner's wallet address", alias="currentOwner")
    new_owner: str = Field(..., description="The new owner's wallet address", alias="newOwner")
    notes: Optional[str] = Field(None, description="Optional notes about the transfer")
    
    model_config = {"populate_by_name": True}

class TransferInitiateResponse(BaseModel):
    status: str = Field(..., description="Status of the transfer initiation")
    message: str = Field(..., description="Message describing the result")
    asset_id: str = Field(..., description="The asset's unique identifier", alias="assetId")
    from_address: str = Field(..., description="The transferor's wallet address", alias="from")
    to_address: str = Field(..., description="The transferee's wallet address", alias="to")
    transaction_id: Optional[str] = Field(None, description="Transaction record ID", alias="transactionId")
    blockchain_tx_hash: Optional[str] = Field(None, description="Blockchain transaction hash", alias="blockchainTxHash")
    
    model_config = {"populate_by_name": True}

class TransferAcceptRequest(BaseModel):
    asset_id: str = Field(..., description="The asset's unique identifier", alias="assetId")
    previous_owner: str = Field(..., description="The previous owner's wallet address", alias="previousOwner")
    new_owner: str = Field(..., description="The new owner's wallet address", alias="newOwner")
    notes: Optional[str] = Field(None, description="Optional notes about the transfer")
    
    model_config = {"populate_by_name": True}

class TransferAcceptResponse(BaseModel):
    status: str = Field(..., description="Status of the transfer acceptance")
    message: str = Field(..., description="Message describing the result")
    asset_id: str = Field(..., description="The asset's unique identifier", alias="assetId")
    from_address: str = Field(..., description="The transferor's wallet address", alias="from")
    to_address: str = Field(..., description="The transferee's wallet address", alias="to")
    transaction_id: Optional[str] = Field(None, description="Transaction record ID", alias="transactionId")
    blockchain_tx_hash: Optional[str] = Field(None, description="Blockchain transaction hash", alias="blockchainTxHash")
    document_id: Optional[str] = Field(None, description="New document ID", alias="documentId")
    version: Optional[int] = Field(None, description="New version number")
    
    model_config = {"populate_by_name": True}

class TransferCancelRequest(BaseModel):
    asset_id: str = Field(..., description="The asset's unique identifier", alias="assetId")
    current_owner: str = Field(..., description="The current owner's wallet address", alias="currentOwner")
    notes: Optional[str] = Field(None, description="Optional notes about the cancellation")
    
    model_config = {"populate_by_name": True}

class TransferCancelResponse(BaseModel):
    status: str = Field(..., description="Status of the transfer cancellation")
    message: str = Field(..., description="Message describing the result")
    asset_id: str = Field(..., description="The asset's unique identifier", alias="assetId")
    from_address: str = Field(..., description="The transferor's wallet address", alias="from")
    to_address: str = Field(..., description="The intended transferee's wallet address", alias="to")
    transaction_id: Optional[str] = Field(None, description="Transaction record ID", alias="transactionId")
    blockchain_tx_hash: Optional[str] = Field(None, description="Blockchain transaction hash", alias="blockchainTxHash")
    
    model_config = {"populate_by_name": True}

class PendingTransferInfo(BaseModel):
    asset_id: str = Field(..., description="The asset's unique identifier", alias="assetId")
    from_address: str = Field(..., description="The transferor's wallet address", alias="from")
    to_address: str = Field(..., description="The transferee's wallet address", alias="to")
    asset_info: Optional[Dict[str, Any]] = Field(None, description="Additional asset information", alias="assetInfo")
    
    model_config = {"populate_by_name": True}

class PendingTransfersResponse(BaseModel):
    wallet_address: str = Field(..., description="The wallet address queried", alias="walletAddress")
    outgoing_transfers: List[PendingTransferInfo] = Field(..., description="List of outgoing transfers", alias="outgoingTransfers")
    incoming_transfers: List[PendingTransferInfo] = Field(..., description="List of incoming transfers", alias="incomingTransfers")
    total_pending: int = Field(..., description="Total number of pending transfers", alias="totalPending")
    
    model_config = {"populate_by_name": True}
