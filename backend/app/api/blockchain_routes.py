from fastapi import APIRouter, Depends, HTTPException, Request
from typing import Dict, Any, Optional
from pydantic import BaseModel
import logging
from web3 import Web3

from app.services.blockchain_service import BlockchainService
from app.services.transaction_state_service import TransactionStateService
from app.services.asset_service import AssetService
from app.services.ipfs_service import IPFSService
from app.services.transaction_service import TransactionService
from app.repositories.asset_repo import AssetRepository
from app.repositories.transaction_repo import TransactionRepository
from app.handlers.upload_handler import UploadHandler
from app.utilities.auth_middleware import get_current_user, get_wallet_address
from app.database import get_db_client

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/blockchain", tags=["blockchain"])

# Pydantic models for request/response schemas
class TransactionPrepareRequest(BaseModel):
    action: str  # "updateIPFS", "deleteAsset", "updateIPFSFor", "deleteAssetFor"
    asset_id: str
    cid: Optional[str] = None  # Required for updateIPFS actions
    owner_address: Optional[str] = None  # Required for "For" actions (delegation)
    gas_limit: Optional[int] = None

class SignedTransactionRequest(BaseModel):
    signed_transaction: str  # Hex string
    action: str
    asset_id: str
    cid: Optional[str] = None
    owner_address: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = {}

class GasEstimationRequest(BaseModel):
    action: str
    asset_id: str
    cid: Optional[str] = None
    owner_address: Optional[str] = None

class TransactionResponse(BaseModel):
    success: bool
    transaction: Optional[Dict[str, Any]] = None
    estimated_gas: Optional[int] = None
    gas_price: Optional[int] = None
    function_name: Optional[str] = None
    error: Optional[str] = None

class BroadcastResponse(BaseModel):
    success: bool
    tx_hash: Optional[str] = None
    block_number: Optional[int] = None
    gas_used: Optional[int] = None
    status: Optional[int] = None
    effective_gas_price: Optional[int] = None
    error: Optional[str] = None

class GasEstimationResponse(BaseModel):
    success: bool
    gas_estimate: Optional[int] = None
    gas_price: Optional[int] = None
    estimated_cost_wei: Optional[int] = None
    estimated_cost_eth: Optional[str] = None
    function_name: Optional[str] = None
    error: Optional[str] = None

def get_blockchain_service() -> BlockchainService:
    """Dependency to get the blockchain service."""
    return BlockchainService()

def get_transaction_state_service() -> TransactionStateService:
    """Dependency to get the transaction state service."""
    return TransactionStateService()

def get_upload_handler_for_blockchain(db_client=Depends(get_db_client)) -> UploadHandler:
    """Dependency to get the upload handler with all required dependencies."""
    asset_repo = AssetRepository(db_client)
    transaction_repo = TransactionRepository(db_client)
    
    asset_service = AssetService(asset_repo)
    ipfs_service = IPFSService()
    blockchain_service = BlockchainService()
    transaction_service = TransactionService(transaction_repo)
    transaction_state_service = TransactionStateService()
    
    return UploadHandler(
        asset_service=asset_service,
        ipfs_service=ipfs_service,
        blockchain_service=blockchain_service,
        transaction_service=transaction_service,
        transaction_state_service=transaction_state_service
    )

@router.post("/prepare-transaction", response_model=TransactionResponse)
async def prepare_transaction(
    request: TransactionPrepareRequest,
    req: Request,
    blockchain_service: BlockchainService = Depends(get_blockchain_service),
    _current_user: Dict[str, Any] = Depends(get_current_user)
) -> TransactionResponse:
    """
    Prepare an unsigned transaction for frontend signing.
    Only available for wallet-authenticated users.
    """
    # Get auth context from request state
    auth_context = getattr(req.state, "auth_context", None)
    
    if not auth_context or auth_context.get("auth_method") != "wallet":
        raise HTTPException(
            status_code=400,
            detail="This endpoint is only for wallet-authenticated users"
        )
    
    try:
        wallet_address = auth_context.get("wallet_address")
        
        if request.action == "updateIPFS":
            if not request.cid:
                raise HTTPException(status_code=400, detail="CID is required for updateIPFS action")
            
            result = await blockchain_service.transaction_builder.build_update_ipfs_transaction(
                asset_id=request.asset_id,
                cid=request.cid,
                from_address=wallet_address,
                gas_limit=request.gas_limit
            )
            
        elif request.action == "updateIPFSFor":
            if not request.cid or not request.owner_address:
                raise HTTPException(status_code=400, detail="CID and owner_address are required for updateIPFSFor action")
            
            result = await blockchain_service.transaction_builder.build_update_ipfs_for_transaction(
                owner_address=request.owner_address,
                asset_id=request.asset_id,
                cid=request.cid,
                from_address=wallet_address,
                gas_limit=request.gas_limit
            )
            
        elif request.action == "deleteAsset":
            result = await blockchain_service.transaction_builder.build_delete_asset_transaction(
                asset_id=request.asset_id,
                from_address=wallet_address,
                gas_limit=request.gas_limit
            )
            
        elif request.action == "deleteAssetFor":
            if not request.owner_address:
                raise HTTPException(status_code=400, detail="owner_address is required for deleteAssetFor action")
            
            result = await blockchain_service.transaction_builder.build_delete_asset_for_transaction(
                owner_address=request.owner_address,
                asset_id=request.asset_id,
                from_address=wallet_address,
                gas_limit=request.gas_limit
            )
            
        else:
            raise HTTPException(status_code=400, detail=f"Unknown action: {request.action}")
        
        if not result.get("success"):
            raise HTTPException(status_code=500, detail=result.get("error", "Unknown error"))
        
        logger.info(f"Transaction prepared for {request.action} on asset {request.asset_id} by {wallet_address}")
        
        return TransactionResponse(**result)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error preparing transaction: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/broadcast-transaction", response_model=BroadcastResponse)
async def broadcast_transaction(
    request: SignedTransactionRequest,
    blockchain_service: BlockchainService = Depends(get_blockchain_service),
    _current_user: Dict[str, Any] = Depends(get_current_user)
) -> BroadcastResponse:
    """
    Broadcast a signed transaction to the blockchain.
    Available for wallet-authenticated users.
    """
    try:
        # Broadcast the signed transaction
        result = await blockchain_service.broadcast_signed_transaction(request.signed_transaction)
        
        logger.info(f"Transaction broadcasted for {request.action} on asset {request.asset_id}")
        
        return BroadcastResponse(**result)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error broadcasting transaction: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/estimate-gas", response_model=GasEstimationResponse)
async def estimate_gas(
    action: str,
    asset_id: str,
    cid: Optional[str] = None,
    owner_address: Optional[str] = None,
    blockchain_service: BlockchainService = Depends(get_blockchain_service),
    wallet_address: str = Depends(get_wallet_address)
) -> GasEstimationResponse:
    """
    Estimate gas costs for a transaction before preparing it.
    Available for wallet-authenticated users.
    """
    try:
        # Validate required parameters for each action
        if action in ["updateIPFS", "updateIPFSFor"] and not cid:
            raise HTTPException(status_code=400, detail="CID is required for updateIPFS actions")
        
        if action in ["updateIPFSFor", "deleteAssetFor"] and not owner_address:
            raise HTTPException(status_code=400, detail="owner_address is required for 'For' actions")
        
        # Prepare kwargs for gas estimation
        kwargs = {"asset_id": asset_id}
        if cid:
            kwargs["cid"] = cid
        if owner_address:
            kwargs["owner_address"] = owner_address
        
        # Get gas estimation
        result = await blockchain_service.transaction_builder.estimate_gas(
            function_name=action,
            from_address=wallet_address,
            **kwargs
        )
        
        if not result.get("success"):
            raise HTTPException(status_code=500, detail=result.get("error", "Gas estimation failed"))
        
        logger.info(f"Gas estimated for {action} on asset {asset_id}: {result.get('gas_estimate')} gas")
        
        return GasEstimationResponse(**result)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error estimating gas: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/verify-transaction/{tx_hash}")
async def verify_transaction(
    tx_hash: str,
    blockchain_service: BlockchainService = Depends(get_blockchain_service),
    _current_user: Dict[str, Any] = Depends(get_current_user)
) -> Dict[str, Any]:
    """
    Verify that a transaction was successful on the blockchain.
    """
    try:
        result = await blockchain_service.verify_transaction_success(tx_hash)
        
        logger.info(f"Transaction {tx_hash} verification: {'success' if result.get('success') else 'failed'}")
        
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error verifying transaction: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/transaction-status/{tx_hash}")
async def get_transaction_status(
    tx_hash: str,
    blockchain_service: BlockchainService = Depends(get_blockchain_service),
    transaction_state_service: TransactionStateService = Depends(get_transaction_state_service),
    upload_handler: UploadHandler = Depends(get_upload_handler_for_blockchain),
    current_user: Dict[str, Any] = Depends(get_current_user)
) -> Dict[str, Any]:
    """
    Get the current status of a transaction (pending, confirmed, failed).
    """
    try:
        # Convert hex string to bytes if necessary
        if isinstance(tx_hash, str) and tx_hash.startswith('0x'):
            tx_hash_bytes = Web3.to_bytes(hexstr=tx_hash)
        else:
            tx_hash_bytes = Web3.to_bytes(hexstr=f"0x{tx_hash}")
        
        # Try to get transaction receipt (indicates transaction is mined)
        try:
            receipt = blockchain_service.web3.eth.get_transaction_receipt(tx_hash_bytes)
            if receipt:
                # Transaction is mined
                success = receipt.status == 1
                
                # If transaction failed, get detailed error info
                error_info = None
                if not success:
                    try:
                        # Get revert reason
                        verification_result = await blockchain_service.verify_transaction_success(tx_hash)
                        error_info = verification_result.get("revert_reason", "Transaction reverted without reason")
                    except Exception as e:
                        error_info = f"Failed to get revert reason: {str(e)}"
                
                logger.info(f"Transaction {tx_hash} status: {'success' if success else 'failed'}. Gas used: {receipt.gasUsed}. Error: {error_info if error_info else 'None'}")
                
                # AUTO-COMPLETION: If transaction succeeded, check for pending batch uploads
                if success:
                    try:
                        user_wallet = current_user.get("walletAddress")
                        if user_wallet:
                            # Check for pending transactions for this user
                            pending_transactions = await transaction_state_service.get_user_pending_transactions(user_wallet)
                            
                            for pending_tx in pending_transactions:
                                # Check if this is a batch upload that matches this specific transaction
                                if (pending_tx.get("operation_type") == "BATCH_CREATE" and 
                                    "metadata" in pending_tx and 
                                    "ipfs_results" in pending_tx["metadata"] and
                                    pending_tx.get("blockchain_tx_hash") == tx_hash):
                                    
                                    logger.info(f"AUTO-COMPLETING BATCH UPLOAD - pending_tx_id: {pending_tx.get('tx_id')}, tx_hash: {tx_hash}")
                                    
                                    # Auto-trigger batch completion
                                    try:
                                        completion_result = await upload_handler.complete_batch_blockchain_upload(
                                            pending_tx_id=pending_tx.get("tx_id"),
                                            blockchain_tx_hash=tx_hash,
                                            initiator_address=user_wallet
                                        )
                                        logger.info(f"AUTO-COMPLETION SUCCESS: {completion_result}")
                                        
                                        # Add completion info to response with frontend-compatible format
                                        result = {
                                            "status": "confirmed",
                                            "success": success,
                                            "auto_completed": True,
                                            "completion_result": completion_result,
                                            "details": {
                                                "tx_hash": tx_hash,
                                                "block_number": receipt.blockNumber,
                                                "gas_used": receipt.gasUsed,
                                                "status": receipt.status,
                                                "message": f"Auto-completed batch upload: {completion_result.get('successful_count', 0)} assets created"
                                            }
                                        }
                                        return result
                                        
                                    except Exception as completion_error:
                                        logger.error(f"AUTO-COMPLETION FAILED: {str(completion_error)}")
                                        # Continue with normal response even if auto-completion fails
                                        break
                    except Exception as auto_complete_error:
                        logger.error(f"Error in auto-completion logic: {str(auto_complete_error)}")
                        # Continue with normal response even if auto-completion check fails
                
                result = {
                    "status": "confirmed",
                    "success": success,
                    "details": {
                        "tx_hash": tx_hash,
                        "block_number": receipt.blockNumber,
                        "gas_used": receipt.gasUsed,
                        "status": receipt.status
                    }
                }
                
                if error_info:
                    result["details"]["error"] = error_info
                
                return result
        except Exception:
            # No receipt means transaction might be pending
            pass
            
        # Check if transaction exists in mempool (pending)
        try:
            tx_data = blockchain_service.web3.eth.get_transaction(tx_hash_bytes)
            if tx_data:
                return {
                    "status": "pending",
                    "details": {
                        "tx_hash": tx_hash,
                        "from": tx_data.get("from"),
                        "to": tx_data.get("to"),
                        "gas": tx_data.get("gas"),
                        "gas_price": tx_data.get("gasPrice")
                    }
                }
        except Exception:
            # Transaction not found in mempool either
            pass
        
        # Transaction not found anywhere
        return {
            "status": "not_found",
            "details": {"tx_hash": tx_hash}
        }
        
    except Exception as e:
        logger.error(f"Error getting transaction status: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))