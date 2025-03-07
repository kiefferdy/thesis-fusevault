from fastapi import APIRouter, Depends, Response, Request, HTTPException
from typing import Dict, Any
import logging

from app.handlers.auth_handler import AuthHandler
from app.schemas.auth_schema import AuthenticationRequest
from app.services.auth_service import AuthService
from app.repositories.auth_repo import AuthRepository
from app.repositories.user_repo import UserRepository
from app.database import get_db_client

# Setup router
router = APIRouter(
    prefix="/auth",
    tags=["Authentication"],
    responses={404: {"description": "Not found"}},
)

logger = logging.getLogger(__name__)

def get_auth_handler(db_client=Depends(get_db_client)) -> AuthHandler:
    """Dependency to get the auth handler with all required dependencies."""
    auth_repo = AuthRepository(db_client)
    user_repo = UserRepository(db_client)
    auth_service = AuthService(auth_repo, user_repo)
    return AuthHandler(auth_service)

@router.get("/nonce/{wallet_address}", response_model=Dict[str, Any])
async def get_nonce(
    wallet_address: str,
    auth_handler: AuthHandler = Depends(get_auth_handler)
) -> Dict[str, Any]:
    """
    Get a nonce for authentication.
    
    Args:
        wallet_address: The wallet address to get a nonce for
        
    Returns:
        Dict containing wallet address and nonce
    """
    return await auth_handler.get_nonce(wallet_address)

@router.post("/login", response_model=Dict[str, Any])
async def authenticate(
    request: AuthenticationRequest,
    response: Response,
    auth_handler: AuthHandler = Depends(get_auth_handler)
) -> Dict[str, Any]:
    """
    Authenticate a user with a signed message.
    
    Args:
        request: Authentication request with wallet address and signature
        
    Returns:
        Dict containing authentication result
    """
    return await auth_handler.authenticate(request, response)

@router.get("/validate", response_model=Dict[str, Any])
async def validate_session(
    request: Request,
    auth_handler: AuthHandler = Depends(get_auth_handler)
) -> Dict[str, Any]:
    """
    Validate the current session.
    
    Returns:
        Session data if valid, or an error
    """
    session_data = await auth_handler.validate_session(request)
    if not session_data:
        raise HTTPException(status_code=401, detail="Invalid or expired session")
    return session_data

@router.post("/logout", response_model=Dict[str, Any])
async def logout(
    request: Request,
    response: Response,
    auth_handler: AuthHandler = Depends(get_auth_handler)
) -> Dict[str, Any]:
    """
    Log out the current user.
    
    Returns:
        Dict containing logout result
    """
    return await auth_handler.logout(request, response)
