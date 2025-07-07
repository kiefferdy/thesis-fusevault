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
    
    # Enhanced owner profile fields
    owner_name: Optional[str] = Field(None, description="Display name of the asset owner", alias="ownerName")
    owner_organization: Optional[str] = Field(None, description="Organization of the asset owner", alias="ownerOrganization")
    owner_job_title: Optional[str] = Field(None, description="Job title of the asset owner", alias="ownerJobTitle")
    owner_bio: Optional[str] = Field(None, description="Bio of the asset owner", alias="ownerBio")
    owner_profile_image: Optional[str] = Field(None, description="Profile image URL of the asset owner", alias="ownerProfileImage")
    owner_location: Optional[str] = Field(None, description="Location of the asset owner", alias="ownerLocation")
    owner_twitter: Optional[str] = Field(None, description="Twitter handle of the asset owner", alias="ownerTwitter")
    owner_linkedin: Optional[str] = Field(None, description="LinkedIn profile of the asset owner", alias="ownerLinkedin")
    owner_github: Optional[str] = Field(None, description="GitHub profile of the asset owner", alias="ownerGithub")
    owner_last_login: Optional[str] = Field(None, description="Last login of the asset owner", alias="ownerLastLogin")
    owner_created_at: Optional[str] = Field(None, description="Account creation date of the asset owner", alias="ownerCreatedAt")
    
    # Enhanced delegate profile fields
    delegate_name: Optional[str] = Field(None, description="Display name of the delegate", alias="delegateName")
    delegate_organization: Optional[str] = Field(None, description="Organization of the delegate", alias="delegateOrganization")
    delegate_job_title: Optional[str] = Field(None, description="Job title of the delegate", alias="delegateJobTitle")
    delegate_bio: Optional[str] = Field(None, description="Bio of the delegate", alias="delegateBio")
    delegate_profile_image: Optional[str] = Field(None, description="Profile image URL of the delegate", alias="delegateProfileImage")
    delegate_location: Optional[str] = Field(None, description="Location of the delegate", alias="delegateLocation")
    delegate_twitter: Optional[str] = Field(None, description="Twitter handle of the delegate", alias="delegateTwitter")
    delegate_linkedin: Optional[str] = Field(None, description="LinkedIn profile of the delegate", alias="delegateLinkedin")
    delegate_github: Optional[str] = Field(None, description="GitHub profile of the delegate", alias="delegateGithub")
    delegate_last_login: Optional[str] = Field(None, description="Last login of the delegate", alias="delegateLastLogin")
    delegate_created_at: Optional[str] = Field(None, description="Account creation date of the delegate", alias="delegateCreatedAt")
    
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

# API Request/Response Models (moved from routes file for proper separation of concerns)

class DelegationStatusResponse(BaseModel):
    is_delegated: bool
    server_wallet_address: str
    user_wallet_address: str
    can_update_assets: bool
    can_delete_assets: bool

class SetDelegationRequest(BaseModel):
    delegate_address: str
    status: bool

class ServerInfoResponse(BaseModel):
    server_wallet_address: str
    network: Dict[str, Any]
    features: Dict[str, Any]

class UserSearchResponse(BaseModel):
    users: List[Dict[str, Any]]
    total: int
    query: str

class UserDelegationRequest(BaseModel):
    delegate_address: str
    status: bool

class UserDelegationResponse(BaseModel):
    owner_address: str
    delegate_address: str
    is_delegated: bool
    transaction_data: Optional[Dict[str, Any]] = None

class DelegateListResponse(BaseModel):
    delegates: List[Dict[str, Any]]
    count: int

class DelegatedAssetsResponse(BaseModel):
    owner_address: str
    owner_username: Optional[str]
    owner_name: Optional[str] = Field(None, description="Display name of the asset owner")
    owner_profile_image: Optional[str] = Field(None, description="Profile image URL of the asset owner")
    owner_organization: Optional[str] = Field(None, description="Organization of the asset owner")
    owner_job_title: Optional[str] = Field(None, description="Job title of the asset owner")
    owner_bio: Optional[str] = Field(None, description="Bio of the asset owner")
    owner_location: Optional[str] = Field(None, description="Location of the asset owner")
    assets: List[Dict[str, Any]]
    total_assets: int

class DelegationConfirmRequest(BaseModel):
    transaction_hash: str
    owner_address: str
    delegate_address: str
    status: bool

class DelegationConfirmResponse(BaseModel):
    success: bool
    message: str
    delegation_id: Optional[str] = None

class DelegationSyncRequest(BaseModel):
    owner_address: str
    delegate_address: str

class DelegationSyncResponse(BaseModel):
    success: bool
    message: str
    was_synced: bool
    delegation_id: Optional[str] = None