from typing import Any, Dict, Optional, List
from pydantic import BaseModel, Field, EmailStr, HttpUrl

class UserBase(BaseModel):
    wallet_address: str = Field(..., description="Ethereum wallet address used for authentication")

class UserCreate(UserBase):
    email: EmailStr = Field(..., description="User's email address")
    role: Optional[str] = Field("user", description="User's role (default: user)")
    name: Optional[str] = Field(None, description="User's full name")
    organization: Optional[str] = Field(None, description="User's organization or company")
    job_title: Optional[str] = Field(None, description="User's job title or position")
    bio: Optional[str] = Field(None, description="User's biography or description")
    profile_image: Optional[HttpUrl] = Field(None, description="URL to user's profile image")
    location: Optional[str] = Field(None, description="User's location or country")
    twitter: Optional[str] = Field(None, description="User's Twitter/X handle")
    linkedin: Optional[str] = Field(None, description="User's LinkedIn profile URL")
    github: Optional[str] = Field(None, description="User's GitHub username")

class UserUpdateRequest(BaseModel):
    email: Optional[EmailStr] = Field(None, description="User's email address")
    role: Optional[str] = Field(None, description="User's role")
    name: Optional[str] = Field(None, description="User's full name")
    organization: Optional[str] = Field(None, description="User's organization or company")
    job_title: Optional[str] = Field(None, description="User's job title or position")
    bio: Optional[str] = Field(None, description="User's biography or description")
    profile_image: Optional[HttpUrl] = Field(None, description="URL to user's profile image")
    location: Optional[str] = Field(None, description="User's location or country")
    twitter: Optional[str] = Field(None, description="User's Twitter/X handle")
    linkedin: Optional[str] = Field(None, description="User's LinkedIn profile URL")
    github: Optional[str] = Field(None, description="User's GitHub username")
    preferences: Optional[Dict[str, Any]] = Field(None, description="User preferences")

class UserResponse(BaseModel):
    status: str = Field(..., description="Status of the request")
    user: Dict[str, Any] = Field(..., description="User information")

class UserProfileResponse(BaseModel):
    id: str = Field(..., description="User ID")
    wallet_address: str = Field(..., description="Ethereum wallet address")
    email: EmailStr = Field(..., description="User's email address")
    role: str = Field(..., description="User's role")
    name: Optional[str] = Field(None, description="User's full name")
    organization: Optional[str] = Field(None, description="User's organization or company")
    job_title: Optional[str] = Field(None, description="User's job title or position")
    bio: Optional[str] = Field(None, description="User's biography or description")
    profile_image: Optional[HttpUrl] = Field(None, description="URL to user's profile image")
    location: Optional[str] = Field(None, description="User's location or country")
    twitter: Optional[str] = Field(None, description="User's Twitter/X handle")
    linkedin: Optional[str] = Field(None, description="User's LinkedIn profile URL")
    github: Optional[str] = Field(None, description="User's GitHub username")
    created_at: Optional[str] = Field(None, description="User creation timestamp")
    last_login: Optional[str] = Field(None, description="Last login timestamp")
    preferences: Optional[Dict[str, Any]] = Field(None, description="User preferences")
    
class UserDeleteResponse(BaseModel):
    status: str = Field(..., description="Status of the delete operation")
    message: str = Field(..., description="Message describing the deletion result")
    wallet_address: str = Field(..., description="Wallet address of the deleted user")

class UsersResponse(BaseModel):
    status: str = Field(..., description="Status of the request")
    role: str = Field(..., description="The role that was queried")
    users: List[Dict[str, Any]] = Field(..., description="List of users with the specified role")
    count: int = Field(..., description="Number of users found")
