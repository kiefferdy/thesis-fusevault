import asyncio
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime
from web3 import Web3
from web3.exceptions import BlockNotFound
from fastapi import HTTPException

from app.config import settings
from app.repositories.delegation_repo import DelegationRepository
from app.schemas.delegation_schema import DelegationEventData

logger = logging.getLogger(__name__)

class DelegationIndexingService:
    """
    Service for indexing delegation events from blockchain and syncing to database.
    Listens for DelegateStatusChanged events and maintains delegation state.
    """
    
    def __init__(self, delegation_repo: DelegationRepository):
        """
        Initialize the delegation indexing service.
        
        Args:
            delegation_repo: Repository for delegation operations
        """
        self.delegation_repo = delegation_repo
        self.web3 = Web3(Web3.HTTPProvider(settings.alchemy_sepolia_url))
        self.contract_address = Web3.to_checksum_address(settings.contract_address)
        
        # DelegateStatusChanged event ABI
        self.delegate_event_abi = {
            "anonymous": False,
            "inputs": [
                {"indexed": True, "internalType": "address", "name": "owner", "type": "address"},
                {"indexed": True, "internalType": "address", "name": "delegate", "type": "address"},
                {"indexed": False, "internalType": "bool", "name": "status", "type": "bool"}
            ],
            "name": "DelegateStatusChanged",
            "type": "event"
        }
        
        # Event signature hash
        self.delegate_event_signature = self.web3.keccak(text="DelegateStatusChanged(address,address,bool)").hex()
        
    async def process_delegation_event(self, event_log: Dict[str, Any]) -> bool:
        """
        Process a single delegation event log and update database.
        
        Args:
            event_log: Raw event log from blockchain
            
        Returns:
            True if processed successfully, False otherwise
        """
        try:
            # Decode the event data
            owner_address = event_log["topics"][1].hex()
            delegate_address = event_log["topics"][2].hex()
            
            # Convert from bytes32 to address format
            owner_address = "0x" + owner_address[-40:]
            delegate_address = "0x" + delegate_address[-40:]
            
            # Decode the status from data field
            status_data = event_log["data"]
            status = bool(int(status_data, 16)) if status_data != "0x" else False
            
            # Get block information
            block_info = await self._get_block_info(event_log["blockNumber"])
            
            # Create event data
            event_data = DelegationEventData(
                owner_address=owner_address,
                delegate_address=delegate_address,
                status=status,
                transaction_hash=event_log["transactionHash"],
                block_number=event_log["blockNumber"],
                block_timestamp=block_info["timestamp"] if block_info else None,
                event_index=event_log["logIndex"]
            )
            
            # Sync to database
            delegation_id = await self.delegation_repo.sync_from_blockchain_event(event_data.dict())
            
            logger.info(
                f"Processed delegation event: {owner_address} -> {delegate_address} = {status} "
                f"(Block #{event_log['blockNumber']}, ID: {delegation_id})"
            )
            
            return True
            
        except Exception as e:
            logger.error(f"Error processing delegation event: {str(e)}")
            return False
    
    async def sync_historical_events(self, from_block: int = 0, to_block: Optional[int] = None) -> int:
        """
        Sync historical delegation events from blockchain to database.
        
        Args:
            from_block: Starting block number (default: 0)
            to_block: Ending block number (default: latest)
            
        Returns:
            Number of events processed
        """
        try:
            if to_block is None:
                to_block = self.web3.eth.get_block('latest')['number']
            
            logger.info(f"Syncing delegation events from block {from_block} to {to_block}")
            
            # Get delegation events in batches to avoid RPC limits
            batch_size = 1000
            processed_count = 0
            
            for start_block in range(from_block, to_block + 1, batch_size):
                end_block = min(start_block + batch_size - 1, to_block)
                
                try:
                    # Get logs for DelegateStatusChanged events
                    logs = self.web3.eth.get_logs({
                        'fromBlock': start_block,
                        'toBlock': end_block,
                        'address': self.contract_address,
                        'topics': [self.delegate_event_signature]
                    })
                    
                    # Process each event
                    for log in logs:
                        # Convert log to dict format
                        event_log = {
                            'topics': [topic.hex() for topic in log['topics']],
                            'data': log['data'].hex(),
                            'blockNumber': log['blockNumber'],
                            'transactionHash': log['transactionHash'].hex(),
                            'logIndex': log['logIndex']
                        }
                        
                        success = await self.process_delegation_event(event_log)
                        if success:
                            processed_count += 1
                    
                    logger.info(f"Processed blocks {start_block} to {end_block}: {len(logs)} events")
                    
                    # Small delay to avoid overwhelming RPC
                    await asyncio.sleep(0.1)
                    
                except Exception as e:
                    logger.error(f"Error processing blocks {start_block} to {end_block}: {str(e)}")
                    continue
            
            logger.info(f"Historical sync completed: {processed_count} delegation events processed")
            return processed_count
            
        except Exception as e:
            logger.error(f"Error syncing historical events: {str(e)}")
            raise
    
    async def sync_recent_events(self, last_synced_block: Optional[int] = None) -> int:
        """
        Sync recent delegation events from the last synced block to current.
        
        Args:
            last_synced_block: Last block that was synced (default: last 100 blocks)
            
        Returns:
            Number of events processed
        """
        try:
            current_block = self.web3.eth.get_block('latest')['number']
            
            if last_synced_block is None:
                # Default to last 100 blocks if no previous sync
                last_synced_block = max(0, current_block - 100)
            
            if last_synced_block >= current_block:
                logger.info("No new blocks to sync")
                return 0
            
            return await self.sync_historical_events(last_synced_block + 1, current_block)
            
        except Exception as e:
            logger.error(f"Error syncing recent events: {str(e)}")
            raise
    
    async def validate_delegation_consistency(self, owner_address: str, delegate_address: str) -> Dict[str, Any]:
        """
        Validate that database state matches blockchain state for a delegation.
        
        Args:
            owner_address: The owner's wallet address
            delegate_address: The delegate's wallet address
            
        Returns:
            Dictionary with validation results
        """
        try:
            # Get blockchain state
            contract = self.web3.eth.contract(
                address=self.contract_address,
                abi=[{
                    "inputs": [
                        {"internalType": "address", "name": "owner", "type": "address"},
                        {"internalType": "address", "name": "delegate", "type": "address"}
                    ],
                    "name": "delegates",
                    "outputs": [{"internalType": "bool", "name": "", "type": "bool"}],
                    "stateMutability": "view",
                    "type": "function"
                }]
            )
            
            blockchain_status = contract.functions.delegates(
                Web3.to_checksum_address(owner_address),
                Web3.to_checksum_address(delegate_address)
            ).call()
            
            # Get database state
            delegation = await self.delegation_repo.get_delegation(owner_address, delegate_address)
            database_status = delegation["isActive"] if delegation else False
            
            is_consistent = blockchain_status == database_status
            
            return {
                "is_consistent": is_consistent,
                "blockchain_status": blockchain_status,
                "database_status": database_status,
                "owner_address": owner_address,
                "delegate_address": delegate_address,
                "delegation_exists_in_db": delegation is not None
            }
            
        except Exception as e:
            logger.error(f"Error validating delegation consistency: {str(e)}")
            raise
    
    async def repair_inconsistent_delegation(self, owner_address: str, delegate_address: str) -> bool:
        """
        Repair delegation inconsistency by syncing blockchain state to database.
        
        Args:
            owner_address: The owner's wallet address
            delegate_address: The delegate's wallet address
            
        Returns:
            True if repaired successfully, False otherwise
        """
        try:
            validation = await self.validate_delegation_consistency(owner_address, delegate_address)
            
            if validation["is_consistent"]:
                logger.info(f"Delegation already consistent: {owner_address} -> {delegate_address}")
                return True
            
            # Sync blockchain state to database
            delegation_data = {
                "ownerAddress": owner_address.lower(),
                "delegateAddress": delegate_address.lower(),
                "isActive": validation["blockchain_status"]
            }
            
            await self.delegation_repo.upsert_delegation(delegation_data)
            
            logger.info(
                f"Repaired delegation: {owner_address} -> {delegate_address} = {validation['blockchain_status']}"
            )
            
            return True
            
        except Exception as e:
            logger.error(f"Error repairing delegation consistency: {str(e)}")
            return False
    
    async def _get_block_info(self, block_number: int) -> Optional[Dict[str, Any]]:
        """
        Get block information including timestamp.
        
        Args:
            block_number: Block number to fetch
            
        Returns:
            Block information or None if not found
        """
        try:
            block = self.web3.eth.get_block(block_number)
            return {
                "number": block["number"],
                "timestamp": datetime.fromtimestamp(block["timestamp"]),
                "hash": block["hash"].hex()
            }
        except BlockNotFound:
            logger.warning(f"Block {block_number} not found")
            return None
        except Exception as e:
            logger.error(f"Error getting block info for {block_number}: {str(e)}")
            return None
    
    async def get_sync_status(self) -> Dict[str, Any]:
        """
        Get the current synchronization status.
        
        Returns:
            Dictionary with sync status information
        """
        try:
            current_block = self.web3.eth.get_block('latest')['number']
            
            # Get total delegations in database
            # Note: This would require adding a count method to the repository
            # For now, we'll estimate based on recent activity
            
            return {
                "current_blockchain_block": current_block,
                "service_status": "running",
                "last_sync_attempt": datetime.utcnow().isoformat(),
                "contract_address": self.contract_address
            }
            
        except Exception as e:
            logger.error(f"Error getting sync status: {str(e)}")
            return {
                "service_status": "error",
                "error": str(e),
                "last_sync_attempt": datetime.utcnow().isoformat()
            }