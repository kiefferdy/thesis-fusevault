from fastapi import APIRouter, Depends
import logging
from typing import Dict, Any

from app.services.ipfs_service import IPFSService
from app.config import settings

# Setup router
router = APIRouter(
    prefix="/debug",
    tags=["Debug"],
    responses={404: {"description": "Not found"}},
)

logger = logging.getLogger(__name__)

@router.get("/health")
async def debug_health():
    """Debug endpoint to check API health."""
    return {
        "status": "OK", 
        "service": "backend",
        "web3_storage_url": settings.web3_storage_service_url
    }

@router.get("/web3-connection")
async def test_web3_connection() -> Dict[str, Any]:
    """Test connection to Web3 storage service."""
    ipfs_service = IPFSService()
    result = await ipfs_service.test_connection()
    return result

@router.get("/config")
async def debug_config():
    """Debug endpoint to check configuration (sanitized)."""
    return {
        "web3_storage_service_url": settings.web3_storage_service_url,
        "cors_origins": settings.cors_origins_list,
        "debug_mode": settings.debug,
        "api_key_auth_enabled": settings.api_key_auth_enabled
    }