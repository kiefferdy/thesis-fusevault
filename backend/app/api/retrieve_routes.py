from fastapi import APIRouter, Depends, Query
from typing import Optional, Dict, Any
import logging

from app.handlers.retrieve_handler import RetrieveHandler
from app.schemas.retrieve_schema import MetadataRetrieveResponse
from app.services.asset_service import AssetService
from app.services.blockchain_service import BlockchainService
from app.services.ipfs_service import IPFSService
from app.services.transaction_service import TransactionService
from app.repositories.asset_repo import AssetRepository
from app.repositories.transaction_repo import TransactionRepository
from app.database import get_db_client
from app.utilities.auth_middleware import get_current_user, check_permission

# Setup router
router = APIRouter(
    prefix="/retrieve",
    tags=["Retrieve"],
    responses={404: {"description": "Not found"}},
)

logger = logging.getLogger(__name__)

def get_retrieve_handler(db_client=Depends(get_db_client)) -> RetrieveHandler:
    """Dependency to get the retrieve handler with all required dependencies."""
    asset_repo = AssetRepository(db_client)
    transaction_repo = TransactionRepository(db_client)
    
    asset_service = AssetService(asset_repo)
    blockchain_service = BlockchainService()
    ipfs_service = IPFSService()
    transaction_service = TransactionService(transaction_repo)
    
    return RetrieveHandler(
        asset_service=asset_service,
        blockchain_service=blockchain_service,
        ipfs_service=ipfs_service,
        transaction_service=transaction_service
    )

@router.get("/{asset_id}", response_model=MetadataRetrieveResponse)
async def retrieve_metadata(
    asset_id: str,
    version: Optional[int] = Query(None, description="Specific version to retrieve"),
    auto_recover: bool = Query(True, description="Whether to automatically recover from tampering"),
    retrieve_handler: RetrieveHandler = Depends(get_retrieve_handler),
    current_user: Dict[str, Any] = Depends(get_current_user),
    read_permission = Depends(check_permission("read"))
) -> MetadataRetrieveResponse:
    """
    Retrieve metadata for an asset and verify its integrity.
    User must be authenticated with 'read' permission to use this endpoint.
    
    If tampering is detected (CID mismatch) and auto_recover is True, authentic data is retrieved from IPFS
    and a new version is created with the recovered data. This only applies to the latest version.
    
    Args:
        asset_id: The asset ID to retrieve metadata for
        version: Optional specific version to retrieve (defaults to current version)
        auto_recover: Whether to automatically recover from tampering (defaults to True)
        current_user: The authenticated user data
        read_permission: Validates user has 'read' permission
        
    Returns:
        MetadataRetrieveResponse containing the verified metadata
    """
    result = await retrieve_handler.retrieve_metadata(asset_id, version, auto_recover)
    return result
