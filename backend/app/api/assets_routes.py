from fastapi import APIRouter, Depends
from typing import Dict, Any, List
import logging

from app.schemas.asset_schema import AssetListResponse
from app.services.asset_service import AssetService
from app.repositories.asset_repo import AssetRepository
from app.database import get_db_client

# Setup router
router = APIRouter(
    prefix="/assets",
    tags=["Assets"],
    responses={404: {"description": "Not found"}},
)

logger = logging.getLogger(__name__)

def get_asset_service(db_client=Depends(get_db_client)) -> AssetService:
    """Dependency to get the asset service with required dependencies."""
    asset_repo = AssetRepository(db_client)
    return AssetService(asset_repo)

@router.get("/user/{wallet_address}", response_model=AssetListResponse)
async def get_user_assets(
    wallet_address: str,
    asset_service: AssetService = Depends(get_asset_service)
) -> AssetListResponse:
    """
    Get all assets owned by a specific wallet address.
    
    Args:
        wallet_address: The wallet address to get assets for
        
    Returns:
        AssetListResponse containing the list of assets owned by the wallet
    """
    try:
        assets = await asset_service.get_user_assets(wallet_address)
        return {"status": "success", "assets": assets}
    except Exception as e:
        logger.error(f"Error getting user assets: {str(e)}")
        # Return empty list instead of error to match frontend expectations
        return {"status": "success", "assets": []}