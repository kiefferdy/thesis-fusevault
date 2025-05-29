from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, Field


class APIKeyBase(BaseModel):
    name: str = Field(..., description="User-friendly name for the API key")
    permissions: List[str] = Field(default=["read"], description="Array of permissions (read, write, delete, admin)")
    expires_at: Optional[datetime] = Field(None, description="Optional expiration date")
    metadata: Optional[dict] = Field(None, description="Additional user-specified information")


class APIKeyCreate(APIKeyBase):
    """Schema for creating a new API key"""
    pass


class APIKeyUpdate(BaseModel):
    """Schema for updating API key permissions"""
    permissions: List[str] = Field(..., description="Updated permissions")


class APIKeyInDB(APIKeyBase):
    """Schema for API key stored in database"""
    key_hash: str = Field(..., description="Hash of the API key")
    wallet_address: str = Field(..., description="The Ethereum wallet address that owns this API key")
    created_at: datetime = Field(default_factory=datetime.utcnow)
    last_used_at: Optional[datetime] = Field(None)
    is_active: bool = Field(True)


class APIKeyResponse(BaseModel):
    """Schema for API key response (without sensitive data)"""
    name: str
    permissions: List[str]
    created_at: datetime
    last_used_at: Optional[datetime]
    expires_at: Optional[datetime]
    is_active: bool
    metadata: Optional[dict]


class APIKeyCreateResponse(APIKeyResponse):
    """Schema for API key creation response (includes the key only once)"""
    api_key: str = Field(..., description="The actual API key (shown only once)")