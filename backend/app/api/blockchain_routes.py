from fastapi import APIRouter, Depends, HTTPException, Request
from typing import Dict, Any, Optional
from pydantic import BaseModel
import logging

from app.services.blockchain_service import BlockchainService
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

@router.post("/prepare-transaction", response_model=TransactionResponse)
async def prepare_transaction(
    request: TransactionPrepareRequest,
    req: Request,
    blockchain_service: BlockchainService = Depends(get_blockchain_service),
    current_user: Dict[str, Any] = Depends(get_current_user)
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
    current_user: Dict[str, Any] = Depends(get_current_user)
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
    current_user: Dict[str, Any] = Depends(get_current_user)
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
    current_user: Dict[str, Any] = Depends(get_current_user)
) -> Dict[str, Any]:
    """
    Get the current status of a transaction (pending, confirmed, failed).
    """
    try:
        # Try to get transaction receipt
        try:
            result = await blockchain_service.verify_transaction_success(tx_hash)
            return {
                "status": "confirmed",
                "success": result.get("success"),
                "details": result
            }
        except Exception:
            # If no receipt yet, check if transaction exists in mempool
            try:
                tx_data = blockchain_service.web3.eth.get_transaction(tx_hash)
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
                pass
            
            return {
                "status": "not_found",
                "details": {"tx_hash": tx_hash}
            }
        
    except Exception as e:
        logger.error(f"Error getting transaction status: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))