import time
import logging
from typing import Dict, Any, Optional
from dataclasses import dataclass, asdict

logger = logging.getLogger(__name__)

@dataclass
class AssetProgress:
    asset_id: str
    status: str  # 'pending', 'uploading', 'completed', 'error'
    progress: int  # 0-100
    ipfs_cid: Optional[str] = None
    error: Optional[str] = None
    updated_at: float = None
    
    def __post_init__(self):
        if self.updated_at is None:
            self.updated_at = time.time()

class BatchProgressTracker:
    """
    In-memory progress tracker for batch uploads.
    In production, this could be replaced with Redis for persistence.
    """
    
    def __init__(self):
        self._batch_progress: Dict[str, Dict[str, AssetProgress]] = {}
        self._batch_metadata: Dict[str, Dict[str, Any]] = {}
    
    def create_batch(self, batch_id: str, asset_ids: list, total_assets: int) -> None:
        """Initialize progress tracking for a new batch."""
        self._batch_progress[batch_id] = {}
        self._batch_metadata[batch_id] = {
            "total_assets": total_assets,
            "completed_count": 0,
            "error_count": 0,
            "created_at": time.time(),
            "blockchain_prepared": False,
            "transaction_data": None,
            "pending_tx_id": None
        }
        
        # Initialize all assets as pending
        for asset_id in asset_ids:
            self._batch_progress[batch_id][asset_id] = AssetProgress(
                asset_id=asset_id,
                status="pending",
                progress=0
            )
        
        logger.info(f"Created batch progress tracking for {batch_id} with {total_assets} assets")
    
    def update_asset_progress(self, batch_id: str, asset_id: str, progress: int, status: str, 
                            ipfs_cid: Optional[str] = None, error: Optional[str] = None) -> None:
        """Update progress for a specific asset in a batch."""
        if batch_id not in self._batch_progress:
            logger.warning(f"Batch {batch_id} not found in progress tracker")
            return
        
        if asset_id not in self._batch_progress[batch_id]:
            logger.warning(f"Asset {asset_id} not found in batch {batch_id}")
            return
        
        # Update asset progress
        old_status = self._batch_progress[batch_id][asset_id].status
        self._batch_progress[batch_id][asset_id] = AssetProgress(
            asset_id=asset_id,
            status=status,
            progress=progress,
            ipfs_cid=ipfs_cid,
            error=error
        )
        
        # Update batch metadata counters
        if old_status != "completed" and status == "completed":
            self._batch_metadata[batch_id]["completed_count"] += 1
        elif old_status != "error" and status == "error":
            self._batch_metadata[batch_id]["error_count"] += 1
        
        logger.debug(f"Updated progress for {batch_id}/{asset_id}: {status} ({progress}%)")
    
    def set_blockchain_prepared(self, batch_id: str, transaction_data: Dict[str, Any], pending_tx_id: str) -> None:
        """Mark blockchain transaction as prepared and store transaction data."""
        if batch_id not in self._batch_metadata:
            logger.warning(f"Batch {batch_id} not found when setting blockchain data")
            return
        
        self._batch_metadata[batch_id]["blockchain_prepared"] = True
        self._batch_metadata[batch_id]["transaction_data"] = transaction_data
        self._batch_metadata[batch_id]["pending_tx_id"] = pending_tx_id
        
        logger.info(f"Blockchain transaction prepared for batch {batch_id}, pending_tx: {pending_tx_id}")
    
    def get_batch_progress(self, batch_id: str) -> Optional[Dict[str, Any]]:
        """Get current progress for a batch."""
        if batch_id not in self._batch_progress:
            return None
        
        # Convert AssetProgress objects to dictionaries
        assets_progress = {
            asset_id: asdict(progress) 
            for asset_id, progress in self._batch_progress[batch_id].items()
        }
        
        return {
            "batch_id": batch_id,
            **self._batch_metadata[batch_id],
            "assets": assets_progress
        }
    
    def is_batch_complete(self, batch_id: str) -> bool:
        """Check if all assets in a batch are completed or errored."""
        if batch_id not in self._batch_progress:
            return False
        
        total = self._batch_metadata[batch_id]["total_assets"]
        completed = self._batch_metadata[batch_id]["completed_count"]
        errors = self._batch_metadata[batch_id]["error_count"]
        
        return (completed + errors) >= total
    
    def cleanup_batch(self, batch_id: str, max_age_seconds: int = 3600) -> None:
        """Remove batch progress data (call after completion or timeout)."""
        if batch_id in self._batch_progress:
            del self._batch_progress[batch_id]
        if batch_id in self._batch_metadata:
            del self._batch_metadata[batch_id]
        logger.info(f"Cleaned up progress tracking for batch {batch_id}")
    
    def cleanup_old_batches(self, max_age_seconds: int = 3600) -> None:
        """Clean up old batch progress data."""
        current_time = time.time()
        expired_batches = []
        
        for batch_id, metadata in self._batch_metadata.items():
            if current_time - metadata["created_at"] > max_age_seconds:
                expired_batches.append(batch_id)
        
        for batch_id in expired_batches:
            self.cleanup_batch(batch_id)
        
        if expired_batches:
            logger.info(f"Cleaned up {len(expired_batches)} expired batches")

# Global instance
progress_tracker = BatchProgressTracker()