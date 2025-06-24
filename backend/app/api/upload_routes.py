from fastapi import APIRouter, Depends, File, Form, UploadFile, Body, HTTPException, Request
from typing import List, Optional, Dict, Any
import logging
import json

from app.handlers.upload_handler import UploadHandler
from app.schemas.upload_schema import (
    MetadataUploadRequest, MetadataUploadResponse, CsvUploadResponse, JsonUploadResponse,
    BatchUploadRequest, BatchUploadResponse, BatchCompletionRequest
)
from app.services.asset_service import AssetService
from app.services.ipfs_service import IPFSService
from app.services.blockchain_service import BlockchainService
from app.services.transaction_service import TransactionService
from app.services.transaction_state_service import TransactionStateService
from app.repositories.asset_repo import AssetRepository
from app.repositories.transaction_repo import TransactionRepository
from app.database import get_db_client
from app.utilities.auth_middleware import get_current_user, get_wallet_address
from pydantic import BaseModel, Field

# Setup router
router = APIRouter(
    prefix="/upload",
    tags=["Upload"],
    responses={404: {"description": "Not found"}},
)

logger = logging.getLogger(__name__)

# Pydantic models for completion endpoints
class UploadCompletionRequest(BaseModel):
    pending_tx_id: str = Field(..., alias="pending_tx_id")
    blockchain_tx_hash: str = Field(..., alias="blockchain_tx_hash")
    
    class Config:
        populate_by_name = True

class PendingTransactionResponse(BaseModel):
    pending_tx_id: str
    status: str
    transaction_data: Optional[Dict[str, Any]] = None
    error: Optional[str] = None

def get_upload_handler(db_client=Depends(get_db_client), request: Request = None) -> UploadHandler:
    """Dependency to get the upload handler with all required dependencies."""
    asset_repo = AssetRepository(db_client)
    transaction_repo = TransactionRepository(db_client)
    
    asset_service = AssetService(asset_repo)
    ipfs_service = IPFSService()
    blockchain_service = BlockchainService()
    transaction_service = TransactionService(transaction_repo)
    transaction_state_service = TransactionStateService()
    
    # Get auth context from request state if available
    auth_context = None
    if request and hasattr(request.state, "auth_context"):
        auth_context = request.state.auth_context
    
    return UploadHandler(
        asset_service=asset_service,
        ipfs_service=ipfs_service,
        blockchain_service=blockchain_service,
        transaction_service=transaction_service,
        transaction_state_service=transaction_state_service,
        auth_context=auth_context
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

@router.post("/complete", response_model=MetadataUploadResponse)
async def complete_upload(
    request: Request,
    upload_handler: UploadHandler = Depends(get_upload_handler),
    current_user: Dict[str, Any] = Depends(get_current_user)
) -> MetadataUploadResponse:
    """
    Complete upload after blockchain transaction is confirmed.
    Only available for wallet-authenticated users.
    """
    logger.info("=== COMPLETION REQUEST STARTED ===")
    logger.info(f"Request URL: {request.url}")
    logger.info(f"Request method: {request.method}")
    
    try:
        # Get raw request body for debugging
        body = await request.body()
        logger.info(f"Raw request body: {body}")
        
        # Parse JSON manually to see what we received
        import json
        raw_data = json.loads(body)
        logger.info(f"Parsed JSON data: {raw_data}")
        
        # Try to create the completion request object
        try:
            completion_request = UploadCompletionRequest(**raw_data)
            logger.info(f"Successfully created UploadCompletionRequest: pending_tx_id={completion_request.pending_tx_id}, blockchain_tx_hash={completion_request.blockchain_tx_hash}")
        except Exception as validation_error:
            logger.error(f"Pydantic validation failed: {validation_error}")
            logger.error(f"Validation error type: {type(validation_error).__name__}")
            raise HTTPException(status_code=422, detail=f"Validation error: {str(validation_error)}")
        
    except json.JSONDecodeError as e:
        logger.error(f"Failed to parse JSON: {e}")
        raise HTTPException(status_code=400, detail=f"Invalid JSON: {str(e)}")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error parsing request: {e}")
        raise HTTPException(status_code=400, detail=f"Error parsing request: {str(e)}")
    
    try:
        # Get the authenticated user's wallet address
        authenticated_wallet = current_user.get("walletAddress")
        
        if not authenticated_wallet:
            raise HTTPException(status_code=401, detail="Unable to determine wallet address")
        
        logger.info(f"Completing upload for pending_tx_id: {completion_request.pending_tx_id}, tx_hash: {completion_request.blockchain_tx_hash}")
        
        # Complete the blockchain upload
        result = await upload_handler.complete_blockchain_upload(
            pending_tx_id=completion_request.pending_tx_id,
            blockchain_tx_hash=completion_request.blockchain_tx_hash,
            initiator_address=authenticated_wallet
        )
        
        logger.info(f"Upload completion result: {result}")
        
        if result.get("status") == "error":
            logger.error(f"Upload completion error: {result.get('detail', 'Unknown error')}")
            raise HTTPException(status_code=400, detail=result.get("detail", "Upload completion failed"))
        
        # Validate the result has required fields before creating response
        if not result.get("assetId") and not result.get("asset_id"):
            logger.error(f"Missing asset_id in result: {result}")
            raise HTTPException(status_code=500, detail="Invalid response: missing asset_id")
        
        return MetadataUploadResponse(**result)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error completing upload: {str(e)}")
        logger.error(f"Exception type: {type(e).__name__}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/pending/{pending_tx_id}", response_model=PendingTransactionResponse)
async def get_pending_transaction(
    pending_tx_id: str,
    current_user: Dict[str, Any] = Depends(get_current_user)
) -> PendingTransactionResponse:
    """
    Get details of a pending transaction.
    Only returns transactions belonging to the authenticated user.
    """
    try:
        # Get the authenticated user's wallet address
        authenticated_wallet = current_user.get("walletAddress")
        
        if not authenticated_wallet:
            raise HTTPException(status_code=401, detail="Unable to determine wallet address")
        
        # Get transaction state service
        transaction_state_service = TransactionStateService()
        
        # Get pending transaction
        pending_data = await transaction_state_service.get_pending_transaction(pending_tx_id)
        
        if not pending_data:
            return PendingTransactionResponse(
                pending_tx_id=pending_tx_id,
                status="not_found",
                error="Pending transaction not found or expired"
            )
        
        # Verify ownership
        if pending_data.get("initiator_address", "").lower() != authenticated_wallet.lower():
            raise HTTPException(status_code=403, detail="Access denied: not your transaction")
        
        return PendingTransactionResponse(
            pending_tx_id=pending_tx_id,
            status="found",
            transaction_data=pending_data
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting pending transaction: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/pending", response_model=List[PendingTransactionResponse])
async def list_pending_transactions(
    current_user: Dict[str, Any] = Depends(get_current_user)
) -> List[PendingTransactionResponse]:
    """
    List all pending transactions for the authenticated user.
    """
    try:
        # Get the authenticated user's wallet address
        authenticated_wallet = current_user.get("walletAddress")
        
        if not authenticated_wallet:
            raise HTTPException(status_code=401, detail="Unable to determine wallet address")
        
        # Get transaction state service
        transaction_state_service = TransactionStateService()
        
        # Get user's pending transactions
        pending_transactions = await transaction_state_service.get_user_pending_transactions(authenticated_wallet)
        
        # Format response
        response = []
        for tx_data in pending_transactions:
            response.append(PendingTransactionResponse(
                pending_tx_id=tx_data.get("tx_id", "unknown"),
                status="found",
                transaction_data=tx_data
            ))
        
        return response
        
    except Exception as e:
        logger.error(f"Error listing pending transactions: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.delete("/pending/{pending_tx_id}")
async def cancel_pending_transaction(
    pending_tx_id: str,
    current_user: Dict[str, Any] = Depends(get_current_user)
) -> Dict[str, str]:
    """
    Cancel a pending transaction.
    Only allows canceling transactions belonging to the authenticated user.
    """
    try:
        # Get the authenticated user's wallet address
        authenticated_wallet = current_user.get("walletAddress")
        
        if not authenticated_wallet:
            raise HTTPException(status_code=401, detail="Unable to determine wallet address")
        
        # Get transaction state service
        transaction_state_service = TransactionStateService()
        
        # Get pending transaction to verify ownership
        pending_data = await transaction_state_service.get_pending_transaction(pending_tx_id)
        
        if not pending_data:
            raise HTTPException(status_code=404, detail="Pending transaction not found or expired")
        
        # Verify ownership
        if pending_data.get("initiator_address", "").lower() != authenticated_wallet.lower():
            raise HTTPException(status_code=403, detail="Access denied: not your transaction")
        
        # Remove the pending transaction
        success = await transaction_state_service.remove_pending_transaction(pending_tx_id)
        
        if success:
            return {"message": "Pending transaction cancelled successfully"}
        else:
            raise HTTPException(status_code=500, detail="Failed to cancel pending transaction")
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error canceling pending transaction: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/batch/prepare", response_model=BatchUploadResponse)
async def prepare_batch_upload(
    request: BatchUploadRequest,
    upload_handler: UploadHandler = Depends(get_upload_handler),
    current_user: Dict[str, Any] = Depends(get_current_user)
) -> BatchUploadResponse:
    """
    Prepare a batch upload requiring blockchain signature.
    
    This endpoint:
    1. Validates all assets in the batch
    2. Uploads metadata to IPFS for all assets
    3. Returns transaction data for MetaMask signing
    """
    # Verify that the authenticated user is the one initiating the upload
    authenticated_wallet = current_user.get("walletAddress")
    if authenticated_wallet.lower() != request.wallet_address.lower():
        logger.warning(f"Unauthorized batch upload attempt: {authenticated_wallet} tried to upload as {request.wallet_address}")
        raise HTTPException(
            status_code=403,
            detail="You can only upload assets for your own wallet address"
        )
    
    try:
        # Convert BatchAssetItem objects to dictionaries
        assets_data = []
        for asset in request.assets:
            assets_data.append({
                "asset_id": asset.asset_id,
                "wallet_address": asset.wallet_address,
                "critical_metadata": asset.critical_metadata,
                "non_critical_metadata": asset.non_critical_metadata or {}
            })
        
        result = await upload_handler.process_batch_metadata(
            assets=assets_data,
            initiator_address=request.wallet_address
        )
        
        return BatchUploadResponse(**result)
        
    except Exception as e:
        logger.error(f"Error in batch upload preparation: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to prepare batch upload: {str(e)}"
        )

@router.post("/batch/complete", response_model=BatchUploadResponse)
async def complete_batch_upload(
    request: BatchCompletionRequest,
    upload_handler: UploadHandler = Depends(get_upload_handler),
    current_user: Dict[str, Any] = Depends(get_current_user)
) -> BatchUploadResponse:
    """
    Complete batch upload after blockchain confirmation.
    Only available for wallet-authenticated users.
    """
    logger.info(f"BATCH COMPLETION ENDPOINT CALLED - pending_tx_id: {request.pending_tx_id}, tx_hash: {request.blockchain_tx_hash}")
    try:
        # Get the authenticated user's wallet address
        authenticated_wallet = current_user.get("walletAddress")
        
        if not authenticated_wallet:
            raise HTTPException(status_code=401, detail="Unable to determine wallet address")
        
        logger.info(f"Completing batch upload for pending_tx_id: {request.pending_tx_id}, tx_hash: {request.blockchain_tx_hash}")
        
        # Complete the batch blockchain upload
        result = await upload_handler.complete_batch_blockchain_upload(
            pending_tx_id=request.pending_tx_id,
            blockchain_tx_hash=request.blockchain_tx_hash,
            initiator_address=authenticated_wallet
        )
        
        logger.info(f"Batch upload completion result: {result}")
        
        if result.get("status") == "error":
            logger.error(f"Batch upload completion error: {result.get('message', 'Unknown error')}")
            raise HTTPException(
                status_code=400,
                detail=result.get("message", "Batch upload completion failed")
            )
        
        return BatchUploadResponse(**result)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error completing batch upload: {str(e)}")
        logger.error(f"Exception type: {type(e).__name__}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/json/batch", response_model=BatchUploadResponse)
async def upload_json_files_batch(
    wallet_address: str = Form(...),
    files: List[UploadFile] = File(...),
    upload_handler: UploadHandler = Depends(get_upload_handler),
    current_user: Dict[str, Any] = Depends(get_current_user)
) -> BatchUploadResponse:
    """
    Upload JSON files using the new batch flow with single MetaMask signature.
    This replaces the old JSON upload endpoint for better UX.
    """
    # Verify that the authenticated user is the one initiating the upload
    authenticated_wallet = current_user.get("walletAddress")
    if authenticated_wallet.lower() != wallet_address.lower():
        logger.warning(f"Unauthorized JSON batch upload attempt: {authenticated_wallet} tried to upload as {wallet_address}")
        raise HTTPException(
            status_code=403,
            detail="You can only upload files for your own wallet address"
        )
    
    try:
        # Parse all JSON files into assets array
        assets_data = []
        for file in files:
            if not file.filename.lower().endswith(".json"):
                raise HTTPException(
                    status_code=400,
                    detail=f"File {file.filename} is not a JSON file"
                )
            
            try:
                content = await file.read()
                data = json.loads(content.decode("utf-8"))
                
                # Validate required fields
                if not data.get("asset_id"):
                    raise ValueError(f"Missing asset_id in {file.filename}")
                if not data.get("critical_metadata"):
                    raise ValueError(f"Missing critical_metadata in {file.filename}")
                
                assets_data.append({
                    "asset_id": data["asset_id"],
                    "wallet_address": data.get("wallet_address", wallet_address),
                    "critical_metadata": data["critical_metadata"],
                    "non_critical_metadata": data.get("non_critical_metadata", {})
                })
                
            except json.JSONDecodeError as e:
                raise HTTPException(
                    status_code=400,
                    detail=f"Invalid JSON in file {file.filename}: {str(e)}"
                )
            except ValueError as e:
                raise HTTPException(
                    status_code=400,
                    detail=f"Validation error in {file.filename}: {str(e)}"
                )
        
        if len(assets_data) > 50:
            raise HTTPException(
                status_code=400,
                detail=f"Too many assets ({len(assets_data)}). Maximum 50 assets per batch."
            )
        
        # Use batch upload flow
        result = await upload_handler.process_batch_metadata(
            assets=assets_data,
            initiator_address=wallet_address
        )
        
        return BatchUploadResponse(**result)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in JSON batch upload: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"JSON batch upload failed: {str(e)}"
        )
