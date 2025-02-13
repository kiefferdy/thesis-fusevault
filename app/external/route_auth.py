import logging
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, EmailStr
from app.core.mongodb_client import MongoDBClient

router = APIRouter(prefix="/auth", tags=["auth"])
db_client = MongoDBClient()

class UserCreate(BaseModel):
    wallet_address: str
    email: EmailStr

@router.post("/register")
async def register_user(wallet_adr: str, user_email: str):
    """Register a new user"""
    try:
        user_id = db_client.create_user(
            wallet_address=wallet_adr,
            email=user_email
        )
        return {"status": "success", "user_id": user_id}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/user/{wallet_address}")
async def get_user(wallet_address: str):
    """Get user by wallet address"""
    try:
        user = db_client.get_user_by_wallet(wallet_address)
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        return user
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))