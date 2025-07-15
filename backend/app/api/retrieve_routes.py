from fastapi import APIRouter, Depends, Query
from fastapi.responses import StreamingResponse
from typing import Optional, Dict, Any, AsyncGenerator
import logging
import asyncio

from app.handlers.retrieve_handler import RetrieveHandler
from app.schemas.retrieve_schema import MetadataRetrieveResponse, ProgressMessage
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
    # Get initiator address for authorization
    initiator_address = current_user.get("walletAddress")
    result = await retrieve_handler.retrieve_metadata(asset_id, version, auto_recover, initiator_address)
    return result


@router.get("/{asset_id}/stream")
async def retrieve_metadata_stream(
    asset_id: str,
    version: Optional[int] = Query(None, description="Specific version to retrieve"),
    auto_recover: bool = Query(True, description="Whether to automatically recover from tampering"),
    api_key: Optional[str] = Query(None, description="API key for authentication (alternative to cookie auth)", alias="key"),
    retrieve_handler: RetrieveHandler = Depends(get_retrieve_handler),
    current_user: Dict[str, Any] = Depends(get_current_user),
    read_permission = Depends(check_permission("read"))
) -> StreamingResponse:
    """
    Stream metadata retrieval progress via Server-Sent Events.
    User must be authenticated with 'read' permission to use this endpoint.
    
    Returns real-time progress updates during the metadata retrieval and verification process.
    The final message contains the complete metadata response.
    
    Args:
        asset_id: The asset ID to retrieve metadata for
        version: Optional specific version to retrieve (defaults to current version)
        auto_recover: Whether to automatically recover from tampering (defaults to True)
        current_user: The authenticated user data
        read_permission: Validates user has 'read' permission
        
    Returns:
        StreamingResponse with Server-Sent Events containing progress updates
    """
    
    async def progress_generator() -> AsyncGenerator[str, None]:
        """Generate Server-Sent Events for metadata retrieval progress."""
        progress_queue = asyncio.Queue()
        result_container = {"result": None, "error": None}
        
        async def progress_callback(step: int, total_steps: int, message: str, completed: bool = False, error: Optional[str] = None) -> None:
            """Progress callback that queues progress messages."""
            await progress_queue.put(ProgressMessage(
                step=step,
                total_steps=total_steps,
                message=message,
                completed=completed,
                error=error
            ))
        
        async def retrieval_task():
            """Task that performs the actual metadata retrieval with progress reporting."""
            try:
                # Get initiator address for authorization
                initiator_address = current_user.get("walletAddress")
                result = await retrieve_handler.retrieve_metadata_with_progress(
                    asset_id, progress_callback, version, auto_recover, initiator_address
                )
                result_container["result"] = result
                # Send completion message
                await progress_callback(9, 9, "Asset retrieval completed", completed=True)
            except Exception as e:
                logger.error(f"Error in streaming retrieval: {str(e)}")
                result_container["error"] = str(e)
                await progress_callback(0, 9, f"Error: {str(e)}", completed=True, error=str(e))
        
        # Start the retrieval task
        task = asyncio.create_task(retrieval_task())
        
        try:
            while True:
                try:
                    # Wait for either a progress message or task completion
                    progress_msg = await asyncio.wait_for(progress_queue.get(), timeout=1.0)
                    yield progress_msg.to_sse_data()
                    
                    if progress_msg.completed:
                        # If operation completed successfully, send final result
                        if result_container["result"] and not progress_msg.error:
                            final_message = ProgressMessage(
                                step=9,
                                total_steps=9,
                                message="Asset retrieval completed",
                                completed=True
                            )
                            yield final_message.to_sse_data()
                            # Optionally include the full result in the final message
                            yield f"data: {result_container['result'].model_dump_json(by_alias=True)}\n\n"
                        break
                        
                except asyncio.TimeoutError:
                    # Check if task is done
                    if task.done():
                        break
                    # Send keepalive
                    yield ": keepalive\n\n"
                    
        except Exception as e:
            logger.error(f"Error in progress generator: {str(e)}")
            error_msg = ProgressMessage(
                step=0,
                total_steps=9,
                message=f"Streaming error: {str(e)}",
                completed=True,
                error=str(e)
            )
            yield error_msg.to_sse_data()
        finally:
            if not task.done():
                task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass
    
    return StreamingResponse(
        progress_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Headers": "Cache-Control"
        }
    )
