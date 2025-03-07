from fastapi import APIRouter, Depends, File, Form, UploadFile
from typing import Dict, Any, List, Optional
import json
import logging

from app.handlers.upload_handler import UploadHandler
from app.services.asset_service import AssetService
from app.services.ipfs_service import IPFSService
from app.services.blockchain_service import BlockchainService
from app.services.transaction_service import TransactionService
from app.repositories.asset_repo import AssetRepository
from app.repositories.transaction_repo import TransactionRepository
from app.database import get_db_client

# Setup router
router = APIRouter(
    prefix="/upload",
    tags=["Uploads"],
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

@router.post("/metadata", response_model=Dict[str, Any])
async def upload_metadata(
    asset_id: str = Form(...),
    wallet_address: str = Form(...),
    critical_metadata: str = Form(...),
    non_critical_metadata: Optional[str] = Form(None),
    upload_handler: UploadHandler = Depends(get_upload_handler)
) -> Dict[str, Any]:
    """
    Upload metadata directly.
    
    Args:
        asset_id: The asset's unique identifier
        wallet_address: The wallet address of the owner
        critical_metadata: JSON string of core metadata 
        non_critical_metadata: JSON string of additional metadata
        
    Returns:
        Dict with processing results
    """
    return await upload_handler.handle_metadata_upload(
        asset_id=asset_id,
        wallet_address=wallet_address,
        critical_metadata=critical_metadata,
        non_critical_metadata=non_critical_metadata
    )

@router.post("/json", response_model=Dict[str, Any])
async def upload_json_files(
    wallet_address: str = Form(...),
    files: List[UploadFile] = File(...),
    upload_handler: UploadHandler = Depends(get_upload_handler)
) -> Dict[str, Any]:
    """
    Upload JSON files.
    
    Args:
        wallet_address: The wallet address of the owner
        files: List of JSON files to upload
        
    Returns:
        Dict with processing results for each file
    """
    return await upload_handler.handle_json_files(
        files=files,
        wallet_address=wallet_address
    )

@router.post("/csv", response_model=Dict[str, Any])
async def upload_csv_files(
    wallet_address: str = Form(...),
    critical_metadata_fields: str = Form(...),
    files: List[UploadFile] = File(...),
    upload_handler: UploadHandler = Depends(get_upload_handler)
) -> Dict[str, Any]:
    """
    Upload CSV files.
    
    Args:
        wallet_address: The wallet address of the owner
        critical_metadata_fields: Comma-separated list of column names to treat as critical metadata
        files: List of CSV files to upload
        
    Returns:
        Dict with processing results for each file
    """
    # Parse critical_metadata_fields from comma-separated string to list
    fields_list = [field.strip() for field in critical_metadata_fields.split(',')]
    
    return await upload_handler.process_csv_upload(
        files=files,
        wallet_address=wallet_address,
        critical_metadata_fields=fields_list
    )

@router.post("/process", response_model=Dict[str, Any])
async def process_metadata(
    asset_id: str,
    wallet_address: str,
    critical_metadata: Dict[str, Any],
    non_critical_metadata: Optional[Dict[str, Any]] = None,
    file_info: Optional[Dict[str, str]] = None,
    upload_handler: UploadHandler = Depends(get_upload_handler)
) -> Dict[str, Any]:
    """
    Process metadata for an asset.
    
    Args:
        asset_id: The asset's unique identifier
        wallet_address: The wallet address of the owner
        critical_metadata: Core metadata that will be stored on blockchain
        non_critical_metadata: Additional metadata stored only in MongoDB
        file_info: Optional information about source file
        
    Returns:
        Dict with processing results
    """
    return await upload_handler.process_metadata(
        asset_id=asset_id,
        wallet_address=wallet_address,
        critical_metadata=critical_metadata,
        non_critical_metadata=non_critical_metadata or {},
        file_info=file_info
    )
