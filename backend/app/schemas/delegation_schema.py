from typing import Any, Dict, Optional, List
from pydantic import BaseModel, Field
from datetime import datetime

class DelegationBase(BaseModel):
    owner_address: str = Field(..., description="Wallet address that owns the assets")
    delegate_address: str = Field(..., description="Wallet address that has been granted delegation")
    is_active: bool = Field(True, description="Whether the delegation is currently active")

class DelegationCreate(DelegationBase):
    transaction_hash: Optional[str] = Field(None, description="Blockchain transaction hash that created this delegation")
    block_number: Optional[int] = Field(None, description="Block number when delegation was created")

class DelegationUpdate(BaseModel):
    is_active: bool = Field(..., description="Whether the delegation is currently active")
    transaction_hash: Optional[str] = Field(None, description="Blockchain transaction hash for the update")
    block_number: Optional[int] = Field(None, description="Block number when delegation was updated")
    updated_at: Optional[datetime] = Field(None, description="When the delegation was last updated")

class DelegationInDB(DelegationBase):
    id: str = Field(..., description="Database document ID")
    transaction_hash: Optional[str] = Field(None, description="Blockchain transaction hash")
    block_number: Optional[int] = Field(None, description="Block number when delegation was created/updated")
    created_at: datetime = Field(..., description="When the delegation was first created")
    updated_at: datetime = Field(..., description="When the delegation was last updated")

class DelegationResponse(BaseModel):
    id: str = Field(..., description="Database document ID")
    owner_address: str = Field(..., description="Wallet address that owns the assets", alias="ownerAddress")
    delegate_address: str = Field(..., description="Wallet address that has been granted delegation", alias="delegateAddress")
    is_active: bool = Field(True, description="Whether the delegation is currently active", alias="isActive")
    owner_username: Optional[str] = Field(None, description="Username of the asset owner", alias="ownerUsername")
    delegate_username: Optional[str] = Field(None, description="Username of the delegate", alias="delegateUsername")
    created_at: datetime = Field(..., description="When the delegation was first created", alias="createdAt")
    updated_at: datetime = Field(..., description="When the delegation was last updated", alias="updatedAt")
    transaction_hash: Optional[str] = Field(None, description="Blockchain transaction hash", alias="transactionHash")
    block_number: Optional[int] = Field(None, description="Block number", alias="blockNumber")

    model_config = {"populate_by_name": True}

class DelegationListResponse(BaseModel):
    delegations: List[DelegationResponse] = Field(..., description="List of delegation relationships")
    count: int = Field(..., description="Total number of delegations")
    owner_address: Optional[str] = Field(None, description="Filter by owner address", alias="ownerAddress")
    delegate_address: Optional[str] = Field(None, description="Filter by delegate address", alias="delegateAddress")

    model_config = {"populate_by_name": True}

class DelegationEventData(BaseModel):
    owner_address: str = Field(..., description="Wallet address that owns the assets")
    delegate_address: str = Field(..., description="Wallet address that has been granted/revoked delegation")
    status: bool = Field(..., description="True for delegation granted, False for revoked")
    transaction_hash: str = Field(..., description="Blockchain transaction hash")
    block_number: int = Field(..., description="Block number when event occurred")
    block_timestamp: Optional[datetime] = Field(None, description="Timestamp of the block")
    event_index: int = Field(..., description="Index of the event within the transaction")

class DelegationStatsResponse(BaseModel):
    total_delegations: int = Field(..., description="Total number of active delegations", alias="totalDelegations")
    delegations_granted: int = Field(..., description="Number of delegations granted by this user", alias="delegationsGranted")
    delegations_received: int = Field(..., description="Number of delegations received by this user", alias="delegationsReceived")
    recent_activity: List[Dict[str, Any]] = Field([], description="Recent delegation activity", alias="recentActivity")

    model_config = {"populate_by_name": True}