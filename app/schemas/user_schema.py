from typing import Optional
from pydantic import BaseModel, Field

class UserBase(BaseModel):
    wallet_address: str = Field(..., description="Ethereum wallet address used for authentication")

class NonceResponse(UserBase):
    nonce: int = Field(..., description="Nonce generated for wallet authentication")

class AuthenticationRequest(UserBase):
    signature: str = Field(..., description="Cryptographic signature provided by the wallet to verify authenticity")

class AuthenticationResponse(UserBase):
    authenticated: bool = Field(..., description="Indicates if authentication was successful")
    message: Optional[str] = Field(None, description="Optional message providing additional details")

    class Config:
        orm_mode = True
