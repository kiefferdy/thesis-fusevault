from pydantic import BaseModel, Field
from datetime import datetime

class UserBase(BaseModel):
    wallet_address: str = Field(..., description="Ethereum wallet address used for authentication")

class NonceResponse(UserBase):
    nonce: int = Field(..., description="Nonce generated for wallet authentication")

class AuthenticationRequest(UserBase):
    signature: str = Field(..., description="Cryptographic signature provided by the wallet to verify authenticity")

class AuthenticationResponse(BaseModel):
    status: str = Field(..., description="Status of the authentication request")
    message: str = Field(..., description="Message describing the authentication result")
    wallet_address: str = Field(..., description="Wallet address that was authenticated")

class SessionResponse(BaseModel):
    wallet_address: str = Field(..., description="Wallet address associated with the session", alias="walletAddress")
    session_id: str = Field(..., description="Session identifier", alias="sessionId")
    created_at: datetime = Field(..., description="When the session was created", alias="createdAt")
    expires_at: datetime = Field(..., description="When the session expires", alias="expiresAt")
    is_active: bool = Field(..., description="Whether the session is active", alias="isActive")

    class Config:
        from_attributes = True
        populate_by_name = True

class LogoutResponse(BaseModel):
    status: str = Field(..., description="Status of the logout request")
    message: str = Field(..., description="Message describing the logout result")
