import logging
import time
from web3 import Web3
from typing import Any, Dict, List
from fastapi import HTTPException

from app.config import settings
from app.services.ipfs_service import IPFSService
from app.utilities.format import format_json, get_ipfs_metadata

logger = logging.getLogger(__name__)

class BaselineService:
    """
    Minimal IPFS + Ethereum service for performance baseline testing.
    Uses same data payloads as FuseVault but with minimal business logic.
    """
    
    def __init__(self):
        self.provider_url = settings.alchemy_sepolia_url
        self.wallet_address = settings.wallet_address
        self.private_key = settings.private_key
        
        # Use deployed baseline contract address
        self.baseline_contract_address = "0x406CeC7740C81D214b0F3db245D75883E983F65d"
        
        # Minimal ABI for baseline contract
        self.baseline_abi = [
            {
                "inputs": [
                    {"internalType": "string", "name": "_assetId", "type": "string"},
                    {"internalType": "string", "name": "_cid", "type": "string"}
                ],
                "name": "storeCID",
                "outputs": [],
                "stateMutability": "nonpayable",
                "type": "function"
            },
            {
                "inputs": [
                    {"internalType": "string[]", "name": "_assetIds", "type": "string[]"},
                    {"internalType": "string[]", "name": "_cids", "type": "string[]"}
                ],
                "name": "batchStoreCIDs",
                "outputs": [],
                "stateMutability": "nonpayable",
                "type": "function"
            },
            {
                "inputs": [
                    {"internalType": "string", "name": "_assetId", "type": "string"}
                ],
                "name": "getCID",
                "outputs": [
                    {"internalType": "string", "name": "", "type": "string"}
                ],
                "stateMutability": "view",
                "type": "function"
            }
        ]
        
        self.web3 = Web3(Web3.HTTPProvider(self.provider_url))
        
        # Only initialize contract if address is set
        if self.baseline_contract_address:
            self.contract = self.web3.eth.contract(
                address=Web3.to_checksum_address(self.baseline_contract_address),
                abi=self.baseline_abi
            )
        else:
            self.contract = None
        
        # Reuse existing IPFS service
        self.ipfs_service = IPFSService()
    
    async def baseline_store_single(self, asset_id: str, metadata: Dict[str, Any]) -> Dict[str, Any]:
        """
        Baseline test: Store single asset using same metadata as FuseVault.
        Measures pure IPFS + Ethereum performance without business logic.
        """
        start_time = time.time()
        
        if not self.contract:
            return {
                "success": False,
                "error": "Baseline contract not deployed. Please deploy BaselineStorage.sol first.",
                "total_time": time.time() - start_time
            }
        
        try:
            # Step 1: Store in IPFS (same as FuseVault)
            ipfs_start = time.time()
            cid = await self.ipfs_service.store_metadata(metadata)
            ipfs_time = time.time() - ipfs_start
            
            # Step 2: Store CID on blockchain (minimal contract)
            blockchain_start = time.time()
            nonce = self.web3.eth.get_transaction_count(self.wallet_address)
            tx = self.contract.functions.storeCID(asset_id, cid).build_transaction({
                'from': self.wallet_address,
                'nonce': nonce,
                'gasPrice': self.web3.eth.gas_price,
                'gas': 200000,  # Much lower gas than FuseVault
            })
            
            signed_tx = self.web3.eth.account.sign_transaction(tx, private_key=self.private_key)
            raw_tx = signed_tx.rawTransaction if hasattr(signed_tx, 'rawTransaction') else signed_tx.raw_transaction
            
            tx_hash = self.web3.eth.send_raw_transaction(raw_tx)
            receipt = self.web3.eth.wait_for_transaction_receipt(tx_hash)
            blockchain_time = time.time() - blockchain_start
            
            total_time = time.time() - start_time
            
            return {
                "success": True,
                "asset_id": asset_id,
                "cid": cid,
                "tx_hash": receipt.transactionHash.hex(),
                "gas_used": receipt.gasUsed,
                "performance": {
                    "total_time": total_time,
                    "ipfs_time": ipfs_time,
                    "blockchain_time": blockchain_time,
                    "ipfs_percentage": (ipfs_time / total_time) * 100,
                    "blockchain_percentage": (blockchain_time / total_time) * 100
                }
            }
            
        except Exception as e:
            logger.error(f"Baseline store failed: {str(e)}")
            return {
                "success": False,
                "error": str(e),
                "total_time": time.time() - start_time
            }
    
    async def baseline_store_batch(self, assets: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Baseline test: Store batch assets using same metadata as FuseVault.
        """
        start_time = time.time()
        batch_size = len(assets)
        
        try:
            # Step 1: Store all in IPFS concurrently (same as FuseVault)
            ipfs_start = time.time()
            ipfs_results = []
            asset_ids = []
            cids = []
            
            for asset in assets:
                asset_id = asset["asset_id"]
                metadata = asset["metadata"]
                
                cid = await self.ipfs_service.store_metadata(metadata)
                ipfs_results.append({"asset_id": asset_id, "cid": cid})
                asset_ids.append(asset_id)
                cids.append(cid)
            
            ipfs_time = time.time() - ipfs_start
            
            # Step 2: Batch store CIDs on blockchain
            blockchain_start = time.time()
            nonce = self.web3.eth.get_transaction_count(self.wallet_address)
            tx = self.contract.functions.batchStoreCIDs(asset_ids, cids).build_transaction({
                'from': self.wallet_address,
                'nonce': nonce,
                'gasPrice': self.web3.eth.gas_price,
                'gas': 200000 + (50000 * batch_size),  # Scale with batch size
            })
            
            signed_tx = self.web3.eth.account.sign_transaction(tx, private_key=self.private_key)
            raw_tx = signed_tx.rawTransaction if hasattr(signed_tx, 'rawTransaction') else signed_tx.raw_transaction
            
            tx_hash = self.web3.eth.send_raw_transaction(raw_tx)
            receipt = self.web3.eth.wait_for_transaction_receipt(tx_hash)
            blockchain_time = time.time() - blockchain_start
            
            total_time = time.time() - start_time
            
            return {
                "success": True,
                "batch_size": batch_size,
                "tx_hash": receipt.transactionHash.hex(),
                "gas_used": receipt.gasUsed,
                "gas_per_asset": receipt.gasUsed / batch_size,
                "assets": ipfs_results,
                "performance": {
                    "total_time": total_time,
                    "ipfs_time": ipfs_time,
                    "blockchain_time": blockchain_time,
                    "throughput_assets_per_sec": batch_size / total_time,
                    "avg_time_per_asset": total_time / batch_size,
                    "ipfs_percentage": (ipfs_time / total_time) * 100,
                    "blockchain_percentage": (blockchain_time / total_time) * 100
                }
            }
            
        except Exception as e:
            logger.error(f"Baseline batch store failed: {str(e)}")
            return {
                "success": False,
                "error": str(e),
                "total_time": time.time() - start_time,
                "batch_size": batch_size
            }
    
    async def baseline_retrieve(self, asset_id: str) -> Dict[str, Any]:
        """
        Baseline test: Retrieve asset data.
        """
        start_time = time.time()
        
        try:
            # Step 1: Get CID from blockchain
            blockchain_start = time.time()
            cid = self.contract.functions.getCID(asset_id).call()
            blockchain_time = time.time() - blockchain_start
            
            if not cid:
                return {
                    "success": False,
                    "error": "Asset not found",
                    "total_time": time.time() - start_time
                }
            
            # Step 2: Retrieve from IPFS
            ipfs_start = time.time()
            metadata = await self.ipfs_service.retrieve_metadata(cid)
            ipfs_time = time.time() - ipfs_start
            
            total_time = time.time() - start_time
            
            return {
                "success": True,
                "asset_id": asset_id,
                "cid": cid,
                "metadata": metadata,
                "performance": {
                    "total_time": total_time,
                    "blockchain_time": blockchain_time,
                    "ipfs_time": ipfs_time,
                    "blockchain_percentage": (blockchain_time / total_time) * 100,
                    "ipfs_percentage": (ipfs_time / total_time) * 100
                }
            }
            
        except Exception as e:
            logger.error(f"Baseline retrieve failed: {str(e)}")
            return {
                "success": False,
                "error": str(e),
                "total_time": time.time() - start_time
            }