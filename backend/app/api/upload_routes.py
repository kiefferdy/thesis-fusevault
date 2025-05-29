from fastapi import APIRouter, Depends, File, Form, UploadFile, Body, HTTPException, Request
from typing import List, Optional, Dict, Any
import logging

from app.handlers.upload_handler import UploadHandler
from app.schemas.upload_schema import MetadataUploadRequest, MetadataUploadResponse, CsvUploadResponse, JsonUploadResponse
from app.services.asset_service import AssetService
from app.services.ipfs_service import IPFSService
from app.services.blockchain_service import BlockchainService
from app.services.transaction_service import TransactionService
from app.repositories.asset_repo import AssetRepository
from app.repositories.transaction_repo import TransactionRepository
from app.database import get_db_client
from app.utilities.auth_middleware import get_current_user, get_wallet_address

# Setup router
router = APIRouter(
    prefix="/upload",
    tags=["Upload"],
    responses={404: {"description": "Not found"}},
)

logger = logging.getLogger(__name__)

def get_upload_handler(db_client=Depends(get_db_client)) -> UploadHandler:
    """Dependency to get the upload handler with all required dependencies."""
    asset_repo = AssetRepository(db_client)
    transaction_repo = TransactionRepository(db_client)
    
    asset_service = AssetService(asset_repo)
    ipfs_service = IPFSService()
    blockchain_service = BlockchainService()
    transaction_service = TransactionService(transaction_repo)
    
    return UploadHandler(
        asset_service=asset_service,
        ipfs_service=ipfs_service,
        blockchain_service=blockchain_service,
        transaction_service=transaction_service
    )

@router.post("/metadata", response_model=MetadataUploadResponse)
async def upload_metadata(
    asset_id: str = Form(...),
    wallet_address: str = Form(...),
    critical_metadata: str = Form(...),
    non_critical_metadata: Optional[str] = Form(None),
    upload_handler: UploadHandler = Depends(get_upload_handler),
    current_user: Dict[str, Any] = Depends(get_current_user)
) -> MetadataUploadResponse:
    """
    Upload metadata directly.
    User must be authenticated to use this endpoint.
    
    Args:
        asset_id: The asset's unique identifier
        wallet_address: The wallet address of the initiator (either the owner or an admin/delegate)
        critical_metadata: JSON string of core metadata 
        non_critical_metadata: JSON string of additional metadata
        current_user: The authenticated user data
        
    Returns:
        MetadataUploadResponse with processing results
    """
    # Verify that the authenticated user is the one initiating the upload
    authenticated_wallet = current_user.get("walletAddress")
    if authenticated_wallet.lower() != wallet_address.lower():
        logger.warning(f"Unauthorized upload attempt: {authenticated_wallet} tried to upload as {wallet_address}")
        raise HTTPException(status_code=403, detail="You can only upload metadata for your own wallet address")
        
    result = await upload_handler.handle_metadata_upload(
        asset_id=asset_id,
        wallet_address=wallet_address,
        critical_metadata=critical_metadata,
        non_critical_metadata=non_critical_metadata
    )
    return MetadataUploadResponse(**result)

@router.post("/json", response_model=JsonUploadResponse)
async def upload_json_files(
    wallet_address: str = Form(...),
    files: List[UploadFile] = File(...),
    upload_handler: UploadHandler = Depends(get_upload_handler),
    current_user: Dict[str, Any] = Depends(get_current_user)
) -> JsonUploadResponse:
    """
    Upload JSON files.
    User must be authenticated to use this endpoint.
    
    Args:
        wallet_address: The wallet address of the initiator (either the owner or an admin/delegate)
        files: List of JSON files to upload. Each JSON must contain:
               - asset_id: The asset's unique identifier
               - wallet_address: The wallet address of the OWNER of this asset
               - critical_metadata: Object containing critical metadata
               - non_critical_metadata: (Optional) Object containing non-critical metadata
        current_user: The authenticated user data
        
    Returns:
        JsonUploadResponse with processing results for each file
    """
    # Verify that the authenticated user is the one initiating the upload
    authenticated_wallet = current_user.get("walletAddress")
    if authenticated_wallet.lower() != wallet_address.lower():
        logger.warning(f"Unauthorized upload attempt: {authenticated_wallet} tried to upload as {wallet_address}")
        raise HTTPException(status_code=403, detail="You can only upload files for your own wallet address")
        
    result = await upload_handler.handle_json_files(
        files=files,
        wallet_address=wallet_address
    )
    return JsonUploadResponse(**result)

@router.post("/csv", response_model=CsvUploadResponse)
async def upload_csv_files(
    wallet_address: str = Form(...),
    critical_metadata_fields: str = Form(...),
    files: List[UploadFile] = File(...),
    upload_handler: UploadHandler = Depends(get_upload_handler),
    current_user: Dict[str, Any] = Depends(get_current_user)
) -> CsvUploadResponse:
    """
    Upload CSV files.
    User must be authenticated to use this endpoint.
    
    Args:
        wallet_address: The wallet address of the initiator (either the owner or an admin/delegate)
        critical_metadata_fields: Comma-separated list of column names to treat as critical metadata
        files: List of CSV files to upload. Each CSV must contain:
               - asset_id: Column with the asset's unique identifier
               - wallet_address: Column with the wallet address of the OWNER of each asset
               - Additional columns specified in critical_metadata_fields
        current_user: The authenticated user data
        
    Returns:
        CsvUploadResponse with processing results for each file
    """
    # Verify that the authenticated user is the one initiating the upload
    authenticated_wallet = current_user.get("walletAddress")
    if authenticated_wallet.lower() != wallet_address.lower():
        logger.warning(f"Unauthorized upload attempt: {authenticated_wallet} tried to upload as {wallet_address}")
        raise HTTPException(status_code=403, detail="You can only upload files for your own wallet address")
        
    # Parse critical_metadata_fields from comma-separated string to list
    fields_list = [field.strip() for field in critical_metadata_fields.split(',')]
    
    result = await upload_handler.process_csv_upload(
        files=files,
        wallet_address=wallet_address,
        critical_metadata_fields=fields_list
    )
    return CsvUploadResponse(**result)

@router.post("/process", response_model=MetadataUploadResponse)
async def process_metadata(
    metadata_request: MetadataUploadRequest = Body(...),
    upload_handler: UploadHandler = Depends(get_upload_handler),
    current_user: Dict[str, Any] = Depends(get_current_user)
) -> MetadataUploadResponse:
    """
    Process metadata for an asset.
    User must be authenticated to use this endpoint.
    
    Args:
        metadata_request: Request containing metadata to process
        current_user: The authenticated user data
        
    Returns:
        MetadataUploadResponse with processing results
    """
    # Verify that the authenticated user is the one initiating the upload
    authenticated_wallet = current_user.get("walletAddress")
    if authenticated_wallet.lower() != metadata_request.wallet_address.lower():
        logger.warning(f"Unauthorized metadata processing attempt: {authenticated_wallet} tried to process as {metadata_request.wallet_address}")
        raise HTTPException(status_code=403, detail="You can only process metadata for your own wallet address")
        
    # For this endpoint, the wallet_address in the request is both the initiator and owner
    # Extract fields from the request
    result = await upload_handler.process_metadata(
        asset_id=metadata_request.asset_id,
        owner_address=metadata_request.wallet_address,
        initiator_address=metadata_request.wallet_address,
        critical_metadata=metadata_request.critical_metadata,
        non_critical_metadata=metadata_request.non_critical_metadata or {},
        file_info=metadata_request.file_info
    )
    return MetadataUploadResponse(**result)
