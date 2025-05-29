from typing import List
from fastapi import APIRouter, Depends, HTTPException, Request, status
import logging

from app.schemas.api_key_schema import (
    APIKeyCreate,
    APIKeyUpdate,
    APIKeyResponse,
    APIKeyCreateResponse
)
from app.services.api_key_service import APIKeyService
from app.repositories.api_key_repo import APIKeyRepository
from app.utilities.auth_middleware import get_current_user, get_wallet_address
from app.database import get_db_client
from app.config import settings

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api-keys", tags=["API Keys"])


def get_api_key_service() -> APIKeyService:
    """Get API key service instance"""
    db_client = get_db_client()
    api_key_repo = APIKeyRepository(db_client.get_collection("api_keys"))
    return APIKeyService(api_key_repo)


@router.post("/create", response_model=APIKeyCreateResponse)
async def create_api_key(
    api_key_data: APIKeyCreate,
    wallet_address: str = Depends(get_wallet_address),
    request: Request = None,
    api_key_service: APIKeyService = Depends(get_api_key_service)
):
    """
    Create a new API key for the authenticated user.
    
    Note: This endpoint requires wallet authentication (not API key auth).
    """
    # Check if API keys are enabled
    if not settings.api_key_auth_enabled:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="API key authentication is not enabled"
        )
    
    # Ensure this is wallet auth, not API key auth
    if hasattr(request.state, "auth_method") and request.state.auth_method == "api_key":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="API keys cannot create other API keys"
        )
    
    try:
        # Create API key
        api_key_response = await api_key_service.create_api_key(
            wallet_address,
            api_key_data
        )
        
        logger.info(f"API key '{api_key_data.name}' created for wallet {wallet_address}")
        return api_key_response
        
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Error creating API key: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create API key"
        )


@router.get("/list", response_model=List[APIKeyResponse])
async def list_api_keys(
    wallet_address: str = Depends(get_wallet_address),
    request: Request = None,
    api_key_service: APIKeyService = Depends(get_api_key_service)
):
    """
    List all API keys for the authenticated user.
    
    Note: This endpoint requires wallet authentication (not API key auth).
    """
    # Ensure this is wallet auth, not API key auth
    if hasattr(request.state, "auth_method") and request.state.auth_method == "api_key":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="API keys cannot list other API keys"
        )
    
    try:
        api_keys = await api_key_service.list_api_keys(wallet_address)
        return api_keys
        
    except Exception as e:
        logger.error(f"Error listing API keys: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to list API keys"
        )


@router.delete("/{key_name}")
async def revoke_api_key(
    key_name: str,
    wallet_address: str = Depends(get_wallet_address),
    request: Request = None,
    api_key_service: APIKeyService = Depends(get_api_key_service)
):
    """
    Revoke an API key by name.
    
    Note: This endpoint requires wallet authentication (not API key auth).
    """
    # Ensure this is wallet auth, not API key auth
    if hasattr(request.state, "auth_method") and request.state.auth_method == "api_key":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="API keys cannot revoke other API keys"
        )
    
    try:
        success = await api_key_service.revoke_api_key(wallet_address, key_name)
        
        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"API key '{key_name}' not found or already revoked"
            )
            
        logger.info(f"API key '{key_name}' revoked for wallet {wallet_address}")
        return {"message": f"API key '{key_name}' revoked successfully"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error revoking API key: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to revoke API key"
        )


@router.put("/{key_name}/permissions")
async def update_api_key_permissions(
    key_name: str,
    permissions_update: APIKeyUpdate,
    wallet_address: str = Depends(get_wallet_address),
    request: Request = None,
    api_key_service: APIKeyService = Depends(get_api_key_service)
):
    """
    Update permissions for an API key.
    
    Note: This endpoint requires wallet authentication (not API key auth).
    """
    # Ensure this is wallet auth, not API key auth
    if hasattr(request.state, "auth_method") and request.state.auth_method == "api_key":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="API keys cannot update permissions"
        )
    
    try:
        success = await api_key_service.update_permissions(
            wallet_address,
            key_name,
            permissions_update.permissions
        )
        
        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"API key '{key_name}' not found or inactive"
            )
            
        logger.info(f"Permissions updated for API key '{key_name}'")
        return {"message": f"Permissions updated for API key '{key_name}'"}
        
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating API key permissions: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update permissions"
        )