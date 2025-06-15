from typing import Dict, Any, Optional, List
import json
import uuid
import logging
from datetime import datetime, timezone, timedelta
import redis
from app.config import settings

logger = logging.getLogger(__name__)

class TransactionStateService:
    """
    Manages pending transactions waiting for user signatures.
    Uses Redis for temporary storage with TTL expiration.
    """
    
    def __init__(self, redis_client: Optional[redis.Redis] = None):
        """
        Initialize the transaction state service.
        
        Args:
            redis_client: Optional Redis client. If None, will create from settings.
        """
        if redis_client:
            self.redis = redis_client
        else:
            # Create Redis client from settings
            if hasattr(settings, 'redis_url') and settings.redis_url:
                self.redis = redis.from_url(settings.redis_url)
            else:
                # Fallback to local Redis
                self.redis = redis.Redis(host='localhost', port=6379, db=0, decode_responses=True)
        
        # Default TTL for pending transactions (5 minutes)
        self.default_ttl = 300
    
    async def store_pending_transaction(
        self,
        user_address: str,
        transaction_data: Dict[str, Any],
        ttl: Optional[int] = None
    ) -> str:
        """
        Store pending transaction data temporarily.
        
        Args:
            user_address: The wallet address of the user
            transaction_data: Transaction data to store
            ttl: Time to live in seconds (default: 5 minutes)
            
        Returns:
            Transaction ID for retrieval
        """
        try:
            # Generate unique transaction ID
            tx_id = f"pending_tx:{user_address.lower()}:{uuid.uuid4()}"
            
            # Add metadata to transaction data
            enhanced_data = {
                **transaction_data,
                "user_address": user_address.lower(),
                "created_at": datetime.now(timezone.utc).isoformat(),
                "tx_id": tx_id
            }
            
            # Store in Redis with TTL
            ttl_seconds = ttl or self.default_ttl
            self.redis.setex(
                tx_id,
                ttl_seconds,
                json.dumps(enhanced_data, default=str)
            )
            
            logger.info(f"Stored pending transaction {tx_id} for user {user_address} with TTL {ttl_seconds}s")
            
            return tx_id
            
        except Exception as e:
            logger.error(f"Error storing pending transaction: {str(e)}")
            raise
    
    async def get_pending_transaction(self, tx_id: str) -> Optional[Dict[str, Any]]:
        """
        Retrieve pending transaction data.
        
        Args:
            tx_id: Transaction ID to retrieve
            
        Returns:
            Transaction data if found, None otherwise
        """
        try:
            data = self.redis.get(tx_id)
            if data:
                parsed_data = json.loads(data)
                logger.info(f"Retrieved pending transaction {tx_id}")
                return parsed_data
            else:
                logger.warning(f"Pending transaction {tx_id} not found or expired")
                return None
                
        except Exception as e:
            logger.error(f"Error retrieving pending transaction {tx_id}: {str(e)}")
            return None
    
    async def update_pending_transaction(
        self,
        tx_id: str,
        update_data: Dict[str, Any],
        extend_ttl: Optional[int] = None
    ) -> bool:
        """
        Update existing pending transaction data.
        
        Args:
            tx_id: Transaction ID to update
            update_data: Data to merge with existing data
            extend_ttl: Optional new TTL in seconds
            
        Returns:
            True if updated successfully, False otherwise
        """
        try:
            # Get existing data
            existing_data = await self.get_pending_transaction(tx_id)
            if not existing_data:
                return False
            
            # Merge with update data
            updated_data = {
                **existing_data,
                **update_data,
                "updated_at": datetime.now(timezone.utc).isoformat()
            }
            
            # Update in Redis
            if extend_ttl:
                self.redis.setex(
                    tx_id,
                    extend_ttl,
                    json.dumps(updated_data, default=str)
                )
            else:
                # Keep existing TTL
                current_ttl = self.redis.ttl(tx_id)
                if current_ttl > 0:
                    self.redis.setex(
                        tx_id,
                        current_ttl,
                        json.dumps(updated_data, default=str)
                    )
                else:
                    # TTL expired or not set, use default
                    self.redis.setex(
                        tx_id,
                        self.default_ttl,
                        json.dumps(updated_data, default=str)
                    )
            
            logger.info(f"Updated pending transaction {tx_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error updating pending transaction {tx_id}: {str(e)}")
            return False
    
    async def remove_pending_transaction(self, tx_id: str) -> bool:
        """
        Remove a pending transaction from storage.
        
        Args:
            tx_id: Transaction ID to remove
            
        Returns:
            True if removed, False if not found
        """
        try:
            result = self.redis.delete(tx_id)
            if result:
                logger.info(f"Removed pending transaction {tx_id}")
                return True
            else:
                logger.warning(f"Pending transaction {tx_id} not found for removal")
                return False
                
        except Exception as e:
            logger.error(f"Error removing pending transaction {tx_id}: {str(e)}")
            return False
    
    async def get_user_pending_transactions(self, user_address: str) -> List[Dict[str, Any]]:
        """
        Get all pending transactions for a user.
        
        Args:
            user_address: The wallet address of the user
            
        Returns:
            List of pending transactions
        """
        try:
            # Search for all transactions for this user
            pattern = f"pending_tx:{user_address.lower()}:*"
            keys = self.redis.keys(pattern)
            
            transactions = []
            for key in keys:
                data = self.redis.get(key)
                if data:
                    try:
                        parsed_data = json.loads(data)
                        transactions.append(parsed_data)
                    except json.JSONDecodeError:
                        logger.warning(f"Invalid JSON data for key {key}")
                        continue
            
            logger.info(f"Found {len(transactions)} pending transactions for user {user_address}")
            return transactions
            
        except Exception as e:
            logger.error(f"Error getting user pending transactions: {str(e)}")
            return []
    
    async def cleanup_expired_transactions(self) -> int:
        """
        Clean up expired transactions (Redis should handle this automatically, but this is a manual cleanup).
        
        Returns:
            Number of transactions cleaned up
        """
        try:
            # Get all pending transaction keys
            pattern = "pending_tx:*"
            keys = self.redis.keys(pattern)
            
            cleaned_count = 0
            for key in keys:
                # Check if key exists and has valid data
                if not self.redis.exists(key):
                    cleaned_count += 1
                    continue
                
                try:
                    data = self.redis.get(key)
                    if not data:
                        self.redis.delete(key)
                        cleaned_count += 1
                        continue
                    
                    parsed_data = json.loads(data)
                    created_at = datetime.fromisoformat(parsed_data.get("created_at", ""))
                    
                    # Check if older than 10 minutes (double the default TTL)
                    if datetime.now(timezone.utc) - created_at > timedelta(minutes=10):
                        self.redis.delete(key)
                        cleaned_count += 1
                        
                except (json.JSONDecodeError, ValueError, TypeError):
                    # Invalid data, remove it
                    self.redis.delete(key)
                    cleaned_count += 1
            
            if cleaned_count > 0:
                logger.info(f"Cleaned up {cleaned_count} expired/invalid pending transactions")
            
            return cleaned_count
            
        except Exception as e:
            logger.error(f"Error during cleanup: {str(e)}")
            return 0
    
    async def get_transaction_stats(self) -> Dict[str, Any]:
        """
        Get statistics about pending transactions.
        
        Returns:
            Dictionary with transaction statistics
        """
        try:
            pattern = "pending_tx:*"
            keys = self.redis.keys(pattern)
            
            total_count = len(keys)
            user_counts = {}
            action_counts = {}
            
            for key in keys:
                try:
                    data = self.redis.get(key)
                    if data:
                        parsed_data = json.loads(data)
                        user_address = parsed_data.get("user_address", "unknown")
                        action = parsed_data.get("action", "unknown")
                        
                        user_counts[user_address] = user_counts.get(user_address, 0) + 1
                        action_counts[action] = action_counts.get(action, 0) + 1
                        
                except (json.JSONDecodeError, TypeError):
                    continue
            
            return {
                "total_pending": total_count,
                "unique_users": len(user_counts),
                "user_distribution": user_counts,
                "action_distribution": action_counts,
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error getting transaction stats: {str(e)}")
            return {
                "total_pending": 0,
                "unique_users": 0,
                "user_distribution": {},
                "action_distribution": {},
                "error": str(e)
            }