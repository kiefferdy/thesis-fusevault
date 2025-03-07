from typing import Optional
from pydantic import BaseModel, Field, EmailStr

class UserBase(BaseModel):
    wallet_address: str = Field(..., description="Ethereum wallet address used for authentication")

class UserCreate(UserBase):
    email: EmailStr = Field(..., description="User's email address")
    role: Optional[str] = Field("user", description="User's role (default: user)")

class UserResponse(UserBase):
    id: str = Field(..., description="Unique identifier for the user")
    email: EmailStr = Field(..., description="User's email address")
    role: str = Field(..., description="User's role")
    
    class Config:
        orm_mode = True
