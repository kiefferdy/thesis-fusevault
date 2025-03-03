from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from app.core.mongodb_client import MongoDBClient
from metamask_auth.nonce_handler import get_nonce, update_nonce
from metamask_auth.verify_signature import verify_signature
import secrets

router = APIRouter(prefix="/metamask", tags=["metamask"])

db_client = MongoDBClient()

class AuthRequest(BaseModel):
    public_address: str
    signature: str

@router.get("/nonce/{public_address}")
async def get_user_nonce(public_address: str):
    """Fetches or creates a nonce for authentication."""
    nonce = get_nonce(public_address)
    return {"public_address": public_address, "nonce": nonce}

@router.post("/authenticate")
async def authenticate_user(request: AuthRequest):
    """Authenticates a user by verifying the signed message."""
    stored_nonce = get_nonce(request.public_address)
    if not stored_nonce:
        raise HTTPException(status_code=404, detail="User not found")
    
    if verify_signature(request.public_address, request.signature, stored_nonce):
        update_nonce(request.public_address)
        return {"status": "success", "message": "Authentication successful"}
    else:
        raise HTTPException(status_code=401, detail="Signature verification failed")