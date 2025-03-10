from typing import Any, Dict, Optional, List
from pydantic import BaseModel, Field, EmailStr

class UserBase(BaseModel):
    wallet_address: str = Field(..., description="Ethereum wallet address used for authentication")

class UserCreate(UserBase):
    email: EmailStr = Field(..., description="User's email address")
    role: Optional[str] = Field("user", description="User's role (default: user)")

class UserUpdateRequest(BaseModel):
    email: Optional[EmailStr] = Field(None, description="User's email address")
    role: Optional[str] = Field(None, description="User's role")
    # Add any other fields that can be updated

class UserResponse(BaseModel):
    status: str = Field(..., description="Status of the request")
    user: Dict[str, Any] = Field(..., description="User information")

class UserDeleteResponse(BaseModel):
    status: str = Field(..., description="Status of the delete operation")
    message: str = Field(..., description="Message describing the deletion result")
    wallet_address: str = Field(..., description="Wallet address of the deleted user")

class UsersResponse(BaseModel):
    status: str = Field(..., description="Status of the request")
    role: str = Field(..., description="The role that was queried")
    users: List[Dict[str, Any]] = Field(..., description="List of users with the specified role")
    count: int = Field(..., description="Number of users found")
