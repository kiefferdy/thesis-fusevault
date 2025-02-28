import logging
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, EmailStr
from typing import Optional
from app.core.mongodb_client import MongoDBClient

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

router = APIRouter(prefix="/auth", tags=["authentication"])
db_client = MongoDBClient()

# Ensure we're using the users collection
users_collection = db_client.users_collection

class UserRegistration(BaseModel):
    wallet_address: str
    email: EmailStr
    role: Optional[str] = "user"

@router.post("/register")
async def register_user(user_data: UserRegistration):
    """Register a new user with wallet address and email"""
    try:
        # Check if user already exists
        existing_user = db_client.get_user_by_wallet(user_data.wallet_address)
        if existing_user:
            return {
                "status": "error", 
                "message": "User with this wallet address already exists",
                "user_id": str(existing_user["_id"])
            }
        
        # Create new user
        user_id = db_client.create_user(
            wallet_address=user_data.wallet_address,
            email=user_data.email,
            role=user_data.role
        )
        
        return {
            "status": "success",
            "message": "User registered successfully",
            "user_id": user_id
        }
    except Exception as e:
        logger.error(f"Error registering user: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/user/{wallet_address}")
async def get_user(wallet_address: str):
    """Get user information by wallet address"""
    try:
        user = db_client.get_user_by_wallet(wallet_address)
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        
        return {
            "status": "success",
            "user": user
        }
    except HTTPException as e:
        raise e
    except Exception as e:
        logger.error(f"Error retrieving user: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))