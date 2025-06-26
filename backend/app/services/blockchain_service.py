import logging
from web3 import Web3
from typing import Any, Dict, Optional
from fastapi import HTTPException

from app.config import settings
from app.services.transaction_builder_service import TransactionBuilderService

logger = logging.getLogger(__name__)

class BlockchainService:
    def __init__(self):
        self.provider_url = settings.alchemy_sepolia_url
        self.wallet_address = settings.wallet_address
        self.private_key = settings.private_key
        self.contract_address = settings.contract_address
        self.contract_abi = [
            # Asset Update Functions
            {
                "inputs": [
                    {"internalType": "string", "name": "_assetId", "type": "string"},
                    {"internalType": "string", "name": "_cid", "type": "string"}
                ],
                "name": "updateIPFS",
                "outputs": [],
                "stateMutability": "nonpayable",
                "type": "function"
            },
            {
                "inputs": [
                    {"internalType": "address", "name": "_owner", "type": "address"},
                    {"internalType": "string", "name": "_assetId", "type": "string"},
                    {"internalType": "string", "name": "_cid", "type": "string"}
                ],
                "name": "updateIPFSFor",
                "outputs": [],
                "stateMutability": "nonpayable",
                "type": "function"
            },

            # Delete Functions
            {
                "inputs": [
                    {"internalType": "string", "name": "_assetId", "type": "string"}
                ],
                "name": "deleteAsset",
                "outputs": [],
                "stateMutability": "nonpayable",
                "type": "function"
            },
            {
                "inputs": [
                    {"internalType": "address", "name": "_owner", "type": "address"},
                    {"internalType": "string", "name": "_assetId", "type": "string"}
                ],
                "name": "deleteAssetFor",
                "outputs": [],
                "stateMutability": "nonpayable",
                "type": "function"
            },

            # Batch Functions
            {
                "inputs": [
                    {"internalType": "string[]", "name": "_assetIds", "type": "string[]"},
                    {"internalType": "string[]", "name": "_cids", "type": "string[]"}
                ],
                "name": "batchUpdateIPFS",
                "outputs": [],
                "stateMutability": "nonpayable",
                "type": "function"
            },
            {
                "inputs": [
                    {"internalType": "address", "name": "_owner", "type": "address"},
                    {"internalType": "string[]", "name": "_assetIds", "type": "string[]"},
                    {"internalType": "string[]", "name": "_cids", "type": "string[]"}
                ],
                "name": "batchUpdateIPFSFor",
                "outputs": [],
                "stateMutability": "nonpayable",
                "type": "function"
            },
            {
                "inputs": [
                    {"internalType": "string[]", "name": "_assetIds", "type": "string[]"}
                ],
                "name": "batchDeleteAssets",
                "outputs": [],
                "stateMutability": "nonpayable",
                "type": "function"
            },
            {
                "inputs": [
                    {"internalType": "address", "name": "_owner", "type": "address"},
                    {"internalType": "string[]", "name": "_assetIds", "type": "string[]"}
                ],
                "name": "batchDeleteAssetsFor",
                "outputs": [],
                "stateMutability": "nonpayable",
                "type": "function"
            },

            # Info and Verification Functions
            {
                "inputs": [
                    {"internalType": "string", "name": "_assetId", "type": "string"},
                    {"internalType": "address", "name": "_owner", "type": "address"}
                ],
                "name": "getIPFSInfo",
                "outputs": [
                    {"internalType": "uint32", "name": "ipfsVersion", "type": "uint32"},
                    {"internalType": "bytes32", "name": "cidHash", "type": "bytes32"},
                    {"internalType": "uint64", "name": "lastUpdated", "type": "uint64"},
                    {"internalType": "uint64", "name": "createdAt", "type": "uint64"},
                    {"internalType": "bool", "name": "isDeleted", "type": "bool"}
                ],
                "stateMutability": "view",
                "type": "function"
            },
            {
                "inputs": [
                    {"internalType": "string", "name": "_assetId", "type": "string"},
                    {"internalType": "address", "name": "_owner", "type": "address"},
                    {"internalType": "string", "name": "_cid", "type": "string"},
                    {"internalType": "uint32", "name": "_claimedIpfsVersion", "type": "uint32"}
                ],
                "name": "verifyCID",
                "outputs": [
                    {"internalType": "bool", "name": "isValid", "type": "bool"},
                    {"internalType": "string", "name": "message", "type": "string"},
                    {"internalType": "uint32", "name": "actualIpfsVersion", "type": "uint32"},
                    {"internalType": "bool", "name": "isDeleted", "type": "bool"}
                ],
                "stateMutability": "view",
                "type": "function"
            },
            {
                "inputs": [
                    {"internalType": "string", "name": "_assetId", "type": "string"},
                    {"internalType": "address", "name": "_owner", "type": "address"}
                ],
                "name": "assetExists",
                "outputs": [
                    {"internalType": "bool", "name": "exists", "type": "bool"},
                    {"internalType": "bool", "name": "isDeleted", "type": "bool"}
                ],
                "stateMutability": "view",
                "type": "function"
            },
            {
                "inputs": [
                    {"internalType": "string", "name": "_assetId", "type": "string"}
                ],
                "name": "hashAssetId",
                "outputs": [
                    {"internalType": "bytes32", "name": "", "type": "bytes32"}
                ],
                "stateMutability": "pure",
                "type": "function"
            },

            # Admin Functions
            {
                "inputs": [
                    {"internalType": "address", "name": "_account", "type": "address"},
                    {"internalType": "bool", "name": "_isAdmin", "type": "bool"}
                ],
                "name": "setAdmin",
                "outputs": [],
                "stateMutability": "nonpayable",
                "type": "function"
            },
            {
                "inputs": [
                    {"internalType": "address", "name": "_delegate", "type": "address"},
                    {"internalType": "bool", "name": "_status", "type": "bool"}
                ],
                "name": "setDelegate",
                "outputs": [],
                "stateMutability": "nonpayable",
                "type": "function"
            },
            {
                "inputs": [
                    {"internalType": "address", "name": "owner", "type": "address"},
                    {"internalType": "address", "name": "delegate", "type": "address"}
                ],
                "name": "delegates",
                "outputs": [
                    {"internalType": "bool", "name": "", "type": "bool"}
                ],
                "stateMutability": "view",
                "type": "function"
            },

            # Transfer Functions
            {
                "inputs": [
                    {"internalType": "string", "name": "_assetId", "type": "string"},
                    {"internalType": "address", "name": "_newOwner", "type": "address"}
                ],
                "name": "initiateTransfer",
                "outputs": [],
                "stateMutability": "nonpayable",
                "type": "function"
            },
            {
                "inputs": [
                    {"internalType": "string", "name": "_assetId", "type": "string"},
                    {"internalType": "address", "name": "_previousOwner", "type": "address"}
                ],
                "name": "acceptTransfer",
                "outputs": [],
                "stateMutability": "nonpayable",
                "type": "function"
            },
            {
                "inputs": [
                    {"internalType": "string", "name": "_assetId", "type": "string"}
                ],
                "name": "cancelTransfer",
                "outputs": [],
                "stateMutability": "nonpayable",
                "type": "function"
            },
            {
                "inputs": [
                    {"internalType": "string", "name": "_assetId", "type": "string"},
                    {"internalType": "address", "name": "_owner", "type": "address"}
                ],
                "name": "getPendingTransfer",
                "outputs": [
                    {"internalType": "address", "name": "pendingTo", "type": "address"}
                ],
                "stateMutability": "view",
                "type": "function"
            },

            # Events
            {
                "anonymous": False,
                "inputs": [
                    {"indexed": True, "internalType": "address", "name": "owner", "type": "address"},
                    {"indexed": True, "internalType": "string", "name": "assetId", "type": "string"},
                    {"indexed": False, "internalType": "uint32", "name": "ipfsVersion", "type": "uint32"},
                    {"indexed": False, "internalType": "string", "name": "cid", "type": "string"},
                    {"indexed": False, "internalType": "bool", "name": "isDeleted", "type": "bool"}
                ],
                "name": "IPFSUpdated",
                "type": "event"
            },
            {
                "anonymous": False,
                "inputs": [
                    {"indexed": True, "internalType": "address", "name": "account", "type": "address"},
                    {"indexed": False, "internalType": "bool", "name": "isAdmin", "type": "bool"}
                ],
                "name": "AdminStatusChanged",
                "type": "event"
            },
            {
                "anonymous": False,
                "inputs": [
                    {"indexed": True, "internalType": "address", "name": "owner", "type": "address"},
                    {"indexed": True, "internalType": "address", "name": "delegate", "type": "address"},
                    {"indexed": False, "internalType": "bool", "name": "status", "type": "bool"}
                ],
                "name": "DelegateStatusChanged",
                "type": "event"
            },
            {
                "anonymous": False,
                "inputs": [
                    {"indexed": True, "internalType": "address", "name": "owner", "type": "address"},
                    {"indexed": True, "internalType": "string", "name": "assetId", "type": "string"},
                    {"indexed": False, "internalType": "uint32", "name": "lastVersion", "type": "uint32"}
                ],
                "name": "AssetDeleted",
                "type": "event"
            },
            {
                "anonymous": False,
                "inputs": [
                    {"indexed": True, "internalType": "address", "name": "from", "type": "address"},
                    {"indexed": True, "internalType": "address", "name": "to", "type": "address"},
                    {"indexed": True, "internalType": "string", "name": "assetId", "type": "string"}
                ],
                "name": "TransferInitiated",
                "type": "event"
            },
            {
                "anonymous": False,
                "inputs": [
                    {"indexed": True, "internalType": "address", "name": "from", "type": "address"},
                    {"indexed": True, "internalType": "address", "name": "to", "type": "address"},
                    {"indexed": True, "internalType": "string", "name": "assetId", "type": "string"}
                ],
                "name": "TransferCompleted",
                "type": "event"
            },
            {
                "anonymous": False,
                "inputs": [
                    {"indexed": True, "internalType": "address", "name": "from", "type": "address"},
                    {"indexed": True, "internalType": "address", "name": "to", "type": "address"},
                    {"indexed": True, "internalType": "string", "name": "assetId", "type": "string"}
                ],
                "name": "TransferCancelled",
                "type": "event"
            }
        ]

        self.web3 = Web3(Web3.HTTPProvider(self.provider_url))

        if not self.web3.is_connected():
            logger.error("Unable to connect to Alchemy Sepolia network.")
            raise HTTPException(status_code=500, detail="Blockchain connection error")

        try:
            self.contract = self.web3.eth.contract(
                address=Web3.to_checksum_address(self.contract_address),
                abi=self.contract_abi
            )
            # Initialize transaction builder service
            self.transaction_builder = TransactionBuilderService(self.web3, self.contract)
        except Exception as e:
            logger.error(f"Error setting up contract: {str(e)}")
            raise

    async def store_hash(self, cid: str, asset_id: str, auth_context: Optional[Dict] = None) -> Dict[str, Any]:
        """
        Store a CID hash on the blockchain for a specific asset.
        
        If auth_context indicates wallet auth, return unsigned transaction.
        If auth_context indicates API key auth or is None, sign and send transaction.
        
        Args:
            cid: The IPFS CID to store
            asset_id: The asset ID this CID is associated with
            auth_context: Optional authentication context
            
        Returns:
            Dict containing transaction hash or unsigned transaction
            
        Raises:
            HTTPException: If blockchain transaction fails
        """
        if auth_context and auth_context.get("auth_method") == "wallet":
            # Return unsigned transaction for frontend signing
            return await self.transaction_builder.build_update_ipfs_transaction(
                asset_id=asset_id,
                cid=cid,
                from_address=auth_context.get("wallet_address")
            )
        else:
            # Existing server-signed logic for API keys
            return await self._store_hash_signed(cid, asset_id)
    
    async def _store_hash_signed(self, cid: str, asset_id: str) -> Dict[str, Any]:
        """
        Store a CID hash on the blockchain using server wallet signature.
        
        Args:
            cid: The IPFS CID to store
            asset_id: The asset ID this CID is associated with
            
        Returns:
            Dict containing transaction hash
            
        Raises:
            HTTPException: If blockchain transaction fails
        """
        try:
            # Build transaction
            nonce = self.web3.eth.get_transaction_count(self.wallet_address)
            tx = self.contract.functions.updateIPFS(
                asset_id,
                cid
            ).build_transaction({
                'from': self.wallet_address,
                'nonce': nonce,
                'gasPrice': self.web3.eth.gas_price,
                'gas': 2000000,
            })

            # Sign transaction
            signed_tx = self.web3.eth.account.sign_transaction(tx, private_key=self.private_key)

            # Different versions of Web3.py use different attribute names
            if hasattr(signed_tx, 'rawTransaction'):
                raw_tx = signed_tx.rawTransaction
            elif hasattr(signed_tx, 'raw_transaction'):
                raw_tx = signed_tx.raw_transaction
            else:
                raw_tx = bytes(signed_tx)

            # Send transaction
            tx_hash = self.web3.eth.send_raw_transaction(raw_tx)

            # Wait for transaction receipt
            receipt = self.web3.eth.wait_for_transaction_receipt(tx_hash)

            logger.info(f"CID successfully stored on blockchain for asset {asset_id}. Transaction hash: {receipt.transactionHash.hex()}")

            return {"tx_hash": receipt.transactionHash.hex()}

        except Exception as e:
            logger.error(f"Blockchain error storing hash: {str(e)}")
            raise HTTPException(status_code=500, detail=f"Blockchain transaction failed: {str(e)}")

    async def store_hash_for(self, cid: str, asset_id: str, owner_address: str, auth_context: Optional[Dict] = None) -> Dict[str, Any]:
        """
        Store a CID hash on the blockchain for a specific asset on behalf of another owner.
        
        If auth_context indicates wallet auth, return unsigned transaction.
        If auth_context indicates API key auth or is None, sign and send transaction.
        
        Args:
            cid: The IPFS CID to store
            asset_id: The asset ID this CID is associated with
            owner_address: The address of the owner
            auth_context: Optional authentication context
            
        Returns:
            Dict containing transaction hash or unsigned transaction
            
        Raises:
            HTTPException: If blockchain transaction fails
        """
        if auth_context and auth_context.get("auth_method") == "wallet":
            # Return unsigned transaction for frontend signing (delegation case)
            return await self.transaction_builder.build_update_ipfs_for_transaction(
                owner_address=owner_address,
                asset_id=asset_id,
                cid=cid,
                from_address=auth_context.get("wallet_address")
            )
        else:
            # Existing server-signed logic for API keys
            return await self._store_hash_for_signed(cid, asset_id, owner_address)
    
    async def _store_hash_for_signed(self, cid: str, asset_id: str, owner_address: str) -> Dict[str, Any]:
        """
        Store a CID hash on the blockchain for another owner using server wallet signature.
        
        Args:
            cid: The IPFS CID to store
            asset_id: The asset ID this CID is associated with
            owner_address: The address of the owner
            
        Returns:
            Dict containing transaction hash
            
        Raises:
            HTTPException: If blockchain transaction fails
        """
        try:
            # Build transaction
            nonce = self.web3.eth.get_transaction_count(self.wallet_address)
            tx = self.contract.functions.updateIPFSFor(
                Web3.to_checksum_address(owner_address),
                asset_id,
                cid
            ).build_transaction({
                'from': self.wallet_address,
                'nonce': nonce,
                'gasPrice': self.web3.eth.gas_price,
                'gas': 2000000,
            })

            # Sign and send the transaction
            signed_tx = self.web3.eth.account.sign_transaction(tx, private_key=self.private_key)
            
            if hasattr(signed_tx, 'rawTransaction'):
                raw_tx = signed_tx.rawTransaction
            elif hasattr(signed_tx, 'raw_transaction'):
                raw_tx = signed_tx.raw_transaction
            else:
                raw_tx = bytes(signed_tx)

            tx_hash = self.web3.eth.send_raw_transaction(raw_tx)
            receipt = self.web3.eth.wait_for_transaction_receipt(tx_hash)

            logger.info(f"CID successfully stored on blockchain for asset {asset_id} owned by {owner_address}. Transaction hash: {receipt.transactionHash.hex()}")

            return {"tx_hash": receipt.transactionHash.hex()}

        except Exception as e:
            logger.error(f"Blockchain error storing hash for another owner: {str(e)}")
            raise HTTPException(status_code=500, detail=f"Blockchain transaction failed: {str(e)}")

    async def delete_asset(self, asset_id: str, auth_context: Optional[Dict] = None) -> Dict[str, Any]:
        """
        Mark an asset as deleted on the blockchain.
        
        If auth_context indicates wallet auth, return unsigned transaction.
        If auth_context indicates API key auth or is None, sign and send transaction.
        
        Args:
            asset_id: The asset ID to delete
            auth_context: Optional authentication context
            
        Returns:
            Dict containing transaction hash or unsigned transaction
            
        Raises:
            HTTPException: If blockchain transaction fails
        """
        if auth_context and auth_context.get("auth_method") == "wallet":
            # Return unsigned transaction for frontend signing
            return await self.transaction_builder.build_delete_asset_transaction(
                asset_id=asset_id,
                from_address=auth_context.get("wallet_address")
            )
        else:
            # Existing server-signed logic for API keys
            return await self._delete_asset_signed(asset_id)
    
    async def _delete_asset_signed(self, asset_id: str) -> Dict[str, Any]:
        """
        Mark an asset as deleted on the blockchain using server wallet signature.
        
        Args:
            asset_id: The asset ID to delete
            
        Returns:
            Dict containing transaction hash
            
        Raises:
            HTTPException: If blockchain transaction fails
        """
        try:
            # Build transaction
            nonce = self.web3.eth.get_transaction_count(self.wallet_address)
            tx = self.contract.functions.deleteAsset(asset_id).build_transaction({
                'from': self.wallet_address,
                'nonce': nonce,
                'gasPrice': self.web3.eth.gas_price,
                'gas': 2000000,
            })

            # Sign and send the transaction
            signed_tx = self.web3.eth.account.sign_transaction(tx, private_key=self.private_key)
            
            if hasattr(signed_tx, 'rawTransaction'):
                raw_tx = signed_tx.rawTransaction
            elif hasattr(signed_tx, 'raw_transaction'):
                raw_tx = signed_tx.raw_transaction
            else:
                raw_tx = bytes(signed_tx)

            tx_hash = self.web3.eth.send_raw_transaction(raw_tx)
            receipt = self.web3.eth.wait_for_transaction_receipt(tx_hash)

            logger.info(f"Asset {asset_id} marked as deleted on blockchain. Transaction hash: {receipt.transactionHash.hex()}")

            return {"tx_hash": receipt.transactionHash.hex()}

        except Exception as e:
            logger.error(f"Blockchain error deleting asset: {str(e)}")
            raise HTTPException(status_code=500, detail=f"Blockchain transaction failed: {str(e)}")

    async def delete_asset_for(self, asset_id: str, owner_address: str, auth_context: Optional[Dict] = None) -> Dict[str, Any]:
        """
        Mark an asset as deleted on the blockchain on behalf of another owner.
        
        If auth_context indicates wallet auth, return unsigned transaction.
        If auth_context indicates API key auth or is None, sign and send transaction.
        
        Args:
            asset_id: The asset ID to delete
            owner_address: The address of the owner
            auth_context: Optional authentication context
            
        Returns:
            Dict containing transaction hash or unsigned transaction
            
        Raises:
            HTTPException: If blockchain transaction fails
        """
        if auth_context and auth_context.get("auth_method") == "wallet":
            # Return unsigned transaction for frontend signing (delegation case)
            return await self.transaction_builder.build_delete_asset_for_transaction(
                owner_address=owner_address,
                asset_id=asset_id,
                from_address=auth_context.get("wallet_address")
            )
        else:
            # Existing server-signed logic for API keys
            return await self._delete_asset_for_signed(asset_id, owner_address)
    
    async def _delete_asset_for_signed(self, asset_id: str, owner_address: str) -> Dict[str, Any]:
        """
        Mark an asset as deleted on the blockchain for another owner using server wallet signature.
        
        Args:
            asset_id: The asset ID to delete
            owner_address: The address of the owner
            
        Returns:
            Dict containing transaction hash
            
        Raises:
            HTTPException: If blockchain transaction fails
        """
        try:
            # Build transaction
            nonce = self.web3.eth.get_transaction_count(self.wallet_address)
            tx = self.contract.functions.deleteAssetFor(
                Web3.to_checksum_address(owner_address),
                asset_id
            ).build_transaction({
                'from': self.wallet_address,
                'nonce': nonce,
                'gasPrice': self.web3.eth.gas_price,
                'gas': 2000000,
            })

            # Sign and send the transaction
            signed_tx = self.web3.eth.account.sign_transaction(tx, private_key=self.private_key)
            
            if hasattr(signed_tx, 'rawTransaction'):
                raw_tx = signed_tx.rawTransaction
            elif hasattr(signed_tx, 'raw_transaction'):
                raw_tx = signed_tx.raw_transaction
            else:
                raw_tx = bytes(signed_tx)

            tx_hash = self.web3.eth.send_raw_transaction(raw_tx)
            receipt = self.web3.eth.wait_for_transaction_receipt(tx_hash)

            logger.info(f"Asset {asset_id} owned by {owner_address} marked as deleted on blockchain. Transaction hash: {receipt.transactionHash.hex()}")

            return {"tx_hash": receipt.transactionHash.hex()}

        except Exception as e:
            logger.error(f"Blockchain error deleting asset for another owner: {str(e)}")
            raise HTTPException(status_code=500, detail=f"Blockchain transaction failed: {str(e)}")

    async def get_transaction_details(self, tx_hash: str, asset_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Get details of a transaction.
        
        Args:
            tx_hash: Transaction hash to query
            
        Returns:
            Dict containing transaction details
            
        Raises:
            HTTPException: If retrieval fails
        """
        try:
            # Convert hex string to bytes if necessary
            if isinstance(tx_hash, str) and tx_hash.startswith('0x'):
                tx_hash_bytes = Web3.to_bytes(hexstr=tx_hash)
            else:
                tx_hash_bytes = Web3.to_bytes(hexstr=f"0x{tx_hash}")
                
            # Get transaction data
            tx_data = self.web3.eth.get_transaction(tx_hash_bytes)
            
            if not tx_data:
                raise ValueError(f"Transaction with hash {tx_hash} not found on blockchain")
                
            # Verify this transaction was sent to our contract
            if tx_data['to'] and tx_data['to'].lower() != self.contract_address.lower():
                raise ValueError(f"Transaction {tx_hash} was not sent to our contract address")
            
            # Get transaction sender
            tx_sender = tx_data.get('from', None)
                
            # Get the input data from the transaction
            input_data = tx_data['input']
            
            # Decode the function call
            try:
                # Try to decode the function call and arguments
                func_obj, func_params = self.contract.decode_function_input(input_data)
                
                # Format the result based on the function called
                result = {
                    "function": func_obj.fn_name,
                    "params": func_params,
                    "tx_hash": tx_hash,
                    "tx_sender": tx_sender.lower() if tx_sender else None,
                    "status": "success"
                }
                
                # For updateIPFS functions, extract asset_id and cid
                if func_obj.fn_name == 'updateIPFS':
                    result["asset_id"] = func_params['_assetId']
                    result["cid"] = func_params['_cid']
                elif func_obj.fn_name == 'updateIPFSFor':
                    result["asset_id"] = func_params['_assetId']
                    result["cid"] = func_params['_cid']
                    result["owner"] = func_params['_owner']
                elif func_obj.fn_name == 'batchUpdateIPFS':
                    result["asset_ids"] = func_params['_assetIds']
                    result["cids"] = func_params['_cids']
                    # If specific asset_id requested, find its CID
                    if asset_id and asset_id in func_params['_assetIds']:
                        asset_index = func_params['_assetIds'].index(asset_id)
                        result["cid"] = func_params['_cids'][asset_index]
                        result["asset_id"] = asset_id
                elif func_obj.fn_name == 'batchUpdateIPFSFor':
                    result["asset_ids"] = func_params['_assetIds']
                    result["cids"] = func_params['_cids']
                    result["owner"] = func_params['_owner']
                    # If specific asset_id requested, find its CID
                    if asset_id and asset_id in func_params['_assetIds']:
                        asset_index = func_params['_assetIds'].index(asset_id)
                        result["cid"] = func_params['_cids'][asset_index]
                        result["asset_id"] = asset_id
                
                return result
                
            except Exception as decode_error:
                logger.error(f"Error decoding transaction input: {str(decode_error)}")
                raise ValueError(f"Could not decode transaction {tx_hash}")
                
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error retrieving transaction details: {str(e)}")
            raise HTTPException(
                status_code=500, 
                detail=f"Failed to retrieve transaction details: {str(e)}"
            )

    async def get_ipfs_info(self, asset_id: str, owner_address: str) -> Dict[str, Any]:
        """
        Get IPFS version information for an asset.
        
        Args:
            asset_id: The asset ID to get info for
            owner_address: The owner's address
            
        Returns:
            Dict containing IPFS version information
        """
        try:
            result = self.contract.functions.getIPFSInfo(
                asset_id,
                Web3.to_checksum_address(owner_address)
            ).call()
            
            # Parse the result tuple
            ipfs_version, cid_hash, last_updated, created_at, is_deleted = result
            
            return {
                "ipfs_version": ipfs_version,
                "cid_hash": "0x" + cid_hash.hex(),
                "last_updated": last_updated,
                "created_at": created_at,
                "is_deleted": is_deleted
            }
        except Exception as e:
            logger.error(f"Error getting IPFS info: {str(e)}")
            raise HTTPException(status_code=500, detail=f"Failed to get IPFS info: {str(e)}")

    async def verify_cid_on_chain(self, asset_id: str, owner_address: str, cid: str, claimed_version: int) -> Dict[str, Any]:
        """
        Verify a CID against blockchain records.
        
        Args:
            asset_id: The asset ID to verify
            owner_address: The owner's address
            cid: The CID to verify
            claimed_version: The version being claimed
            
        Returns:
            Dict containing verification results
        """
        try:
            result = self.contract.functions.verifyCID(
                asset_id,
                Web3.to_checksum_address(owner_address),
                cid,
                claimed_version
            ).call()
            
            # Parse the result tuple
            is_valid, message, actual_version, is_deleted = result
            
            return {
                "is_valid": is_valid,
                "message": message,
                "actual_version": actual_version,
                "is_deleted": is_deleted
            }
        except Exception as e:
            logger.error(f"Error verifying CID on chain: {str(e)}")
            raise HTTPException(status_code=500, detail=f"Failed to verify CID: {str(e)}")

    async def check_asset_exists(self, asset_id: str, owner_address: str) -> Dict[str, bool]:
        """
        Check if an asset exists on the blockchain.
        
        Args:
            asset_id: The asset ID to check
            owner_address: The owner's address
            
        Returns:
            Dict containing existence and deletion status
        """
        try:
            result = self.contract.functions.assetExists(
                asset_id,
                Web3.to_checksum_address(owner_address)
            ).call()
            
            exists, is_deleted = result
            
            return {
                "exists": exists,
                "is_deleted": is_deleted
            }
        except Exception as e:
            logger.error(f"Error checking if asset exists: {str(e)}")
            raise HTTPException(status_code=500, detail=f"Failed to check if asset exists: {str(e)}")

    async def set_admin(self, account_address: str, is_admin: bool) -> Dict[str, Any]:
        """
        Set or remove an admin.
        
        Args:
            account_address: The address to set as admin
            is_admin: Whether to set or remove admin status
            
        Returns:
            Dict containing transaction hash
        """
        try:
            # Build transaction
            nonce = self.web3.eth.get_transaction_count(self.wallet_address)
            tx = self.contract.functions.setAdmin(
                Web3.to_checksum_address(account_address),
                is_admin
            ).build_transaction({
                'from': self.wallet_address,
                'nonce': nonce,
                'gasPrice': self.web3.eth.gas_price,
                'gas': 2000000,
            })

            # Sign and send the transaction
            signed_tx = self.web3.eth.account.sign_transaction(tx, private_key=self.private_key)
            
            if hasattr(signed_tx, 'rawTransaction'):
                raw_tx = signed_tx.rawTransaction
            elif hasattr(signed_tx, 'raw_transaction'):
                raw_tx = signed_tx.raw_transaction
            else:
                raw_tx = bytes(signed_tx)

            tx_hash = self.web3.eth.send_raw_transaction(raw_tx)
            receipt = self.web3.eth.wait_for_transaction_receipt(tx_hash)

            action = "set" if is_admin else "removed"
            logger.info(f"Admin status {action} for {account_address}. Transaction hash: {receipt.transactionHash.hex()}")

            return {"tx_hash": receipt.transactionHash.hex()}

        except Exception as e:
            logger.error(f"Blockchain error setting admin status: {str(e)}")
            raise HTTPException(status_code=500, detail=f"Blockchain transaction failed: {str(e)}")

    async def set_delegate(self, delegate_address: str, status: bool) -> Dict[str, Any]:
        """
        Set or remove a delegate.
        
        Args:
            delegate_address: The address to set as delegate
            status: Whether to set or remove delegate status
            
        Returns:
            Dict containing transaction hash
        """
        try:
            # Build transaction
            nonce = self.web3.eth.get_transaction_count(self.wallet_address)
            tx = self.contract.functions.setDelegate(
                Web3.to_checksum_address(delegate_address),
                status
            ).build_transaction({
                'from': self.wallet_address,
                'nonce': nonce,
                'gasPrice': self.web3.eth.gas_price,
                'gas': 2000000,
            })

            # Sign and send the transaction
            signed_tx = self.web3.eth.account.sign_transaction(tx, private_key=self.private_key)
            
            if hasattr(signed_tx, 'rawTransaction'):
                raw_tx = signed_tx.rawTransaction
            elif hasattr(signed_tx, 'raw_transaction'):
                raw_tx = signed_tx.raw_transaction
            else:
                raw_tx = bytes(signed_tx)

            tx_hash = self.web3.eth.send_raw_transaction(raw_tx)
            receipt = self.web3.eth.wait_for_transaction_receipt(tx_hash)

            action = "added" if status else "removed"
            logger.info(f"Delegate {delegate_address} {action}. Transaction hash: {receipt.transactionHash.hex()}")

            return {"tx_hash": receipt.transactionHash.hex()}

        except Exception as e:
            logger.error(f"Blockchain error setting delegate status: {str(e)}")
            raise HTTPException(status_code=500, detail=f"Blockchain transaction failed: {str(e)}")

    async def initiate_transfer(self, asset_id: str, new_owner: str) -> Dict[str, Any]:
        """
        Initiate transfer of an asset to a new owner.
        
        Args:
            asset_id: The asset ID to transfer
            new_owner: The address of the new owner
            
        Returns:
            Dict containing transaction hash
        """
        try:
            # Build transaction
            nonce = self.web3.eth.get_transaction_count(self.wallet_address)
            tx = self.contract.functions.initiateTransfer(
                asset_id,
                Web3.to_checksum_address(new_owner)
            ).build_transaction({
                'from': self.wallet_address,
                'nonce': nonce,
                'gasPrice': self.web3.eth.gas_price,
                'gas': 2000000,
            })

            # Sign and send the transaction
            signed_tx = self.web3.eth.account.sign_transaction(tx, private_key=self.private_key)
            
            if hasattr(signed_tx, 'rawTransaction'):
                raw_tx = signed_tx.rawTransaction
            elif hasattr(signed_tx, 'raw_transaction'):
                raw_tx = signed_tx.raw_transaction
            else:
                raw_tx = bytes(signed_tx)

            tx_hash = self.web3.eth.send_raw_transaction(raw_tx)
            receipt = self.web3.eth.wait_for_transaction_receipt(tx_hash)

            logger.info(f"Transfer initiated for asset {asset_id} to {new_owner}. Transaction hash: {receipt.transactionHash.hex()}")

            return {"tx_hash": receipt.transactionHash.hex()}

        except Exception as e:
            logger.error(f"Blockchain error initiating transfer: {str(e)}")
            raise HTTPException(status_code=500, detail=f"Blockchain transaction failed: {str(e)}")

    async def accept_transfer(self, asset_id: str, previous_owner: str) -> Dict[str, Any]:
        """
        Accept transfer of an asset from previous owner.
        
        Args:
            asset_id: The asset ID to accept
            previous_owner: The address of the previous owner
            
        Returns:
            Dict containing transaction hash
        """
        try:
            # Build transaction
            nonce = self.web3.eth.get_transaction_count(self.wallet_address)
            tx = self.contract.functions.acceptTransfer(
                asset_id,
                Web3.to_checksum_address(previous_owner)
            ).build_transaction({
                'from': self.wallet_address,
                'nonce': nonce,
                'gasPrice': self.web3.eth.gas_price,
                'gas': 2000000,
            })

            # Sign and send the transaction
            signed_tx = self.web3.eth.account.sign_transaction(tx, private_key=self.private_key)
            
            if hasattr(signed_tx, 'rawTransaction'):
                raw_tx = signed_tx.rawTransaction
            elif hasattr(signed_tx, 'raw_transaction'):
                raw_tx = signed_tx.raw_transaction
            else:
                raw_tx = bytes(signed_tx)

            tx_hash = self.web3.eth.send_raw_transaction(raw_tx)
            receipt = self.web3.eth.wait_for_transaction_receipt(tx_hash)

            logger.info(f"Transfer accepted for asset {asset_id} from {previous_owner}. Transaction hash: {receipt.transactionHash.hex()}")

            return {"tx_hash": receipt.transactionHash.hex()}

        except Exception as e:
            logger.error(f"Blockchain error accepting transfer: {str(e)}")
            raise HTTPException(status_code=500, detail=f"Blockchain transaction failed: {str(e)}")

    async def cancel_transfer(self, asset_id: str) -> Dict[str, Any]:
        """
        Cancel a pending transfer.
        
        Args:
            asset_id: The asset ID to cancel transfer for
            
        Returns:
            Dict containing transaction hash
        """
        try:
            # Build transaction
            nonce = self.web3.eth.get_transaction_count(self.wallet_address)
            tx = self.contract.functions.cancelTransfer(asset_id).build_transaction({
                'from': self.wallet_address,
                'nonce': nonce,
                'gasPrice': self.web3.eth.gas_price,
                'gas': 2000000,
            })

            # Sign and send the transaction
            signed_tx = self.web3.eth.account.sign_transaction(tx, private_key=self.private_key)
            
            if hasattr(signed_tx, 'rawTransaction'):
                raw_tx = signed_tx.rawTransaction
            elif hasattr(signed_tx, 'raw_transaction'):
                raw_tx = signed_tx.raw_transaction
            else:
                raw_tx = bytes(signed_tx)

            tx_hash = self.web3.eth.send_raw_transaction(raw_tx)
            receipt = self.web3.eth.wait_for_transaction_receipt(tx_hash)

            logger.info(f"Transfer cancelled for asset {asset_id}. Transaction hash: {receipt.transactionHash.hex()}")

            return {"tx_hash": receipt.transactionHash.hex()}

        except Exception as e:
            logger.error(f"Blockchain error cancelling transfer: {str(e)}")
            raise HTTPException(status_code=500, detail=f"Blockchain transaction failed: {str(e)}")

    async def get_pending_transfer(self, asset_id: str, owner_address: str) -> str:
        """
        Get pending transfer address for an asset.
        
        Args:
            asset_id: The asset ID to check
            owner_address: The current owner's address
            
        Returns:
            Address the asset is pending transfer to, or zero address if none
        """
        try:
            pending_to = self.contract.functions.getPendingTransfer(
                asset_id,
                Web3.to_checksum_address(owner_address)
            ).call()
            
            return pending_to
            
        except Exception as e:
            logger.error(f"Error getting pending transfer: {str(e)}")
            raise HTTPException(status_code=500, detail=f"Failed to get pending transfer: {str(e)}")
            
    async def broadcast_signed_transaction(self, signed_transaction: str) -> Dict[str, Any]:
        """
        Broadcast a signed transaction to the blockchain.
        
        Args:
            signed_transaction: The signed transaction as hex string
            
        Returns:
            Dict containing transaction details
            
        Raises:
            HTTPException: If broadcasting fails
        """
        try:
            # Convert hex string to bytes if needed
            if isinstance(signed_transaction, str):
                if signed_transaction.startswith('0x'):
                    signed_tx_bytes = bytes.fromhex(signed_transaction[2:])
                else:
                    signed_tx_bytes = bytes.fromhex(signed_transaction)
            else:
                signed_tx_bytes = signed_transaction
            
            # Send transaction
            tx_hash = self.web3.eth.send_raw_transaction(signed_tx_bytes)
            
            # Wait for transaction receipt
            receipt = self.web3.eth.wait_for_transaction_receipt(tx_hash)
            
            logger.info(f"Signed transaction broadcasted successfully. Transaction hash: {receipt.transactionHash.hex()}")
            
            return {
                "success": True,
                "tx_hash": receipt.transactionHash.hex(),
                "block_number": receipt.blockNumber,
                "gas_used": receipt.gasUsed,
                "status": receipt.status,
                "effective_gas_price": receipt.effectiveGasPrice if hasattr(receipt, 'effectiveGasPrice') else None
            }
            
        except Exception as e:
            logger.error(f"Error broadcasting signed transaction: {str(e)}")
            raise HTTPException(status_code=500, detail=f"Failed to broadcast transaction: {str(e)}")
    
    async def verify_transaction_success(self, tx_hash: str) -> Dict[str, Any]:
        """
        Verify that a transaction was successful.
        
        Args:
            tx_hash: The transaction hash to verify
            
        Returns:
            Dict containing verification results
            
        Raises:
            HTTPException: If verification fails
        """
        try:
            # Convert hex string to bytes if necessary
            if isinstance(tx_hash, str) and tx_hash.startswith('0x'):
                tx_hash_bytes = Web3.to_bytes(hexstr=tx_hash)
            else:
                tx_hash_bytes = Web3.to_bytes(hexstr=f"0x{tx_hash}")
                
            # Get transaction receipt
            receipt = self.web3.eth.get_transaction_receipt(tx_hash_bytes)
            
            if not receipt:
                # More detailed error message for missing transactions
                chain_id = self.web3.eth.chain_id
                network_name = "Sepolia" if chain_id == 11155111 else f"Chain {chain_id}"
                raise ValueError(
                    f"Transaction with hash '{tx_hash}' not found on {network_name}. "
                    f"This typically means: (1) The transaction was sent to a different network, "
                    f"(2) The transaction is still pending, or (3) The transaction failed to send. "
                    f"Please verify your wallet was connected to Sepolia when the transaction was sent."
                )
                
            # Check if transaction was successful
            success = receipt.status == 1
            
            result = {
                "success": success,
                "tx_hash": tx_hash,
                "block_number": receipt.blockNumber,
                "gas_used": receipt.gasUsed,
                "status": receipt.status,
                "contract_address": receipt.contractAddress if hasattr(receipt, 'contractAddress') else None
            }
            
            # If transaction failed, try to get revert reason
            if not success:
                try:
                    # Get the transaction data
                    tx_data = self.web3.eth.get_transaction(tx_hash_bytes)
                    
                    # Try to call the transaction to get revert reason
                    call_result = self.web3.eth.call(
                        {
                            'to': tx_data['to'],
                            'from': tx_data['from'],
                            'data': tx_data['input'],
                            'gas': tx_data['gas'],
                            'gasPrice': tx_data['gasPrice'] if 'gasPrice' in tx_data else tx_data['maxFeePerGas'],
                            'value': tx_data['value']
                        },
                        receipt.blockNumber - 1  # Call at block before the failed transaction
                    )
                except Exception as revert_error:
                    revert_reason = str(revert_error)
                    if "execution reverted" in revert_reason.lower():
                        # Extract the actual revert message
                        if "revert" in revert_reason:
                            revert_msg = revert_reason.split("revert")[-1].strip()
                            result["revert_reason"] = revert_msg
                        else:
                            result["revert_reason"] = revert_reason
                    else:
                        result["revert_reason"] = f"Transaction failed: {revert_reason}"
                
                logger.error(f"Transaction {tx_hash} failed. Gas used: {receipt.gasUsed}. Revert reason: {result.get('revert_reason', 'Unknown')}")
            else:
                logger.info(f"Transaction {tx_hash} verification: success")
            
            return result
            
        except Exception as e:
            logger.error(f"Error verifying transaction {tx_hash}: {str(e)}")
            if "not found" in str(e).lower():
                # Re-raise transaction not found errors with original message
                raise HTTPException(status_code=404, detail=str(e))
            else:
                raise HTTPException(status_code=500, detail=f"Failed to verify transaction: {str(e)}")
    
    async def check_delegation(self, owner_address: str, delegate_address: str) -> bool:
        """
        Check if an address has been delegated by the owner.
        
        Args:
            owner_address: The address of the owner
            delegate_address: The address to check delegation for
            
        Returns:
            True if delegated, False otherwise
        """
        try:
            # Call the delegates mapping on the contract
            is_delegated = self.contract.functions.delegates(
                Web3.to_checksum_address(owner_address),
                Web3.to_checksum_address(delegate_address)
            ).call()
            
            logger.info(
                f"Delegation check: {owner_address} -> {delegate_address} = {is_delegated}"
            )
            
            return is_delegated
            
        except Exception as e:
            logger.error(f"Error checking delegation: {str(e)}")
            raise HTTPException(
                status_code=500, 
                detail=f"Failed to check delegation: {str(e)}"
            )

    async def check_server_delegation(self, user_address: str) -> bool:
        """
        Check if the user has delegated the server wallet for API key usage.
        
        Args:
            user_address: The address of the user
            
        Returns:
            True if user has delegated server wallet, False otherwise
        """
        return await self.check_delegation(user_address, self.wallet_address)

    async def check_two_step_delegation(self, owner_address: str, api_key_user_address: str) -> Dict[str, bool]:
        """
        Check both required delegations for API key usage (two-step delegation model).
        
        Args:
            owner_address: The address of the asset owner
            api_key_user_address: The address of the API key user
            
        Returns:
            Dict with delegation status for both user and server wallet
        """
        try:
            # Check both delegations in parallel for efficiency
            user_delegated_task = self.check_delegation(owner_address, api_key_user_address)
            server_delegated_task = self.check_delegation(owner_address, self.wallet_address)
            
            is_user_delegated = await user_delegated_task
            is_server_delegated = await server_delegated_task
            
            return {
                "user_delegated": is_user_delegated,
                "server_delegated": is_server_delegated,
                "both_delegated": is_user_delegated and is_server_delegated,
                "api_key_user": api_key_user_address,
                "server_wallet": self.wallet_address
            }
            
        except Exception as e:
            logger.error(f"Error checking two-step delegation: {str(e)}")
            raise HTTPException(
                status_code=500, 
                detail=f"Failed to check delegation: {str(e)}"
            )

    def get_server_wallet_address(self) -> str:
        """
        Get the server's wallet address used for signing transactions.
        
        Returns:
            Server wallet address
        """
        return self.wallet_address

    async def prepare_batch_transaction(
        self, 
        asset_ids: list, 
        cids: list, 
        from_address: str
    ) -> Dict[str, Any]:
        """
        Prepare an unsigned batch transaction for wallet authentication (MetaMask signing).
        Always uses batchUpdateIPFS function for wallet auth.
        
        Args:
            asset_ids: List of asset IDs
            cids: List of IPFS CIDs
            from_address: Wallet address of the user (who will sign)
            
        Returns:
            Dict containing unsigned transaction and gas estimates
        """
        try:
            if len(asset_ids) != len(cids):
                raise ValueError("Asset IDs and CIDs arrays must have the same length")
            
            if len(asset_ids) == 0:
                raise ValueError("Must provide at least one asset")
            
            if len(asset_ids) > 50:  # MAX_BATCH_SIZE from contract
                raise ValueError("Batch size cannot exceed 50 assets")
            
            # For wallet auth, always use batchUpdateIPFS (user owns the assets)
            contract_function = self.contract.functions.batchUpdateIPFS(asset_ids, cids)
            
            # Build transaction
            nonce = self.web3.eth.get_transaction_count(Web3.to_checksum_address(from_address))
            gas_price = self.web3.eth.gas_price
            
            # Estimate gas
            estimated_gas = contract_function.estimate_gas({
                'from': Web3.to_checksum_address(from_address),
                'gasPrice': gas_price
            })
            
            # Add 20% buffer to gas estimate
            gas_limit = int(estimated_gas * 1.2)
            
            # Build the unsigned transaction
            transaction = contract_function.build_transaction({
                'from': Web3.to_checksum_address(from_address),
                'nonce': nonce,
                'gasPrice': gas_price,
                'gas': gas_limit,
            })
            
            logger.info(f"Prepared batch transaction for {len(asset_ids)} assets from {from_address}")
            
            return {
                "success": True,
                "transaction": transaction,
                "estimated_gas": estimated_gas,
                "gas_limit": gas_limit,
                "gas_price": gas_price,
                "function_name": "batchUpdateIPFS",
                "asset_count": len(asset_ids)
            }
            
        except Exception as e:
            logger.error(f"Error preparing batch transaction: {str(e)}")
            return {
                "success": False,
                "error": str(e)
            }

    async def execute_batch_transaction(
        self, 
        asset_ids: list, 
        cids: list, 
        owner_addresses: list = None
    ) -> Dict[str, Any]:
        """
        Execute a batch transaction with server wallet signature for API key authentication.
        Uses batchUpdateIPFSFor if owner_addresses provided, otherwise batchUpdateIPFS.
        
        Args:
            asset_ids: List of asset IDs
            cids: List of IPFS CIDs  
            owner_addresses: List of owner addresses (for API key auth - assets owned by users)
            
        Returns:
            Dict containing transaction hash
        """
        try:
            if len(asset_ids) != len(cids):
                raise ValueError("Asset IDs and CIDs arrays must have the same length")
            
            if len(asset_ids) == 0:
                raise ValueError("Must provide at least one asset")
            
            if len(asset_ids) > 50:  # MAX_BATCH_SIZE from contract
                raise ValueError("Batch size cannot exceed 50 assets")
            
            # For API key auth, we need to use batchUpdateIPFSFor because:
            # - Server wallet signs the transaction
            # - But assets should be owned by the API key user's wallet
            if owner_addresses:
                if len(owner_addresses) != len(asset_ids):
                    raise ValueError("Owner addresses array must have the same length as asset IDs")
                
                # Use batchUpdateIPFSFor - all assets must have the same owner for this function
                unique_owners = list(set(owner_addresses))
                if len(unique_owners) != 1:
                    raise ValueError("All assets in a batch must have the same owner for API key authentication")
                
                owner_address = unique_owners[0]
                contract_function = self.contract.functions.batchUpdateIPFSFor(
                    Web3.to_checksum_address(owner_address),
                    asset_ids,
                    cids
                )
                logger.info(f"Executing batch transaction for {len(asset_ids)} assets owned by {owner_address}")
            else:
                # Fallback to batchUpdateIPFS (server owns assets - probably not desired)
                contract_function = self.contract.functions.batchUpdateIPFS(asset_ids, cids)
                logger.warning(f"Executing batch transaction with server as owner - this may not be intended")
            
            # Build transaction
            nonce = self.web3.eth.get_transaction_count(self.wallet_address)
            gas_price = self.web3.eth.gas_price
            
            # Estimate gas
            estimated_gas = contract_function.estimate_gas({
                'from': self.wallet_address,
                'gasPrice': gas_price
            })
            
            # Add 20% buffer to gas estimate
            gas_limit = int(estimated_gas * 1.2)
            
            # Build and sign transaction
            tx = contract_function.build_transaction({
                'from': self.wallet_address,
                'nonce': nonce,
                'gasPrice': gas_price,
                'gas': gas_limit,
            })
            
            # Sign transaction
            signed_tx = self.web3.eth.account.sign_transaction(tx, private_key=self.private_key)
            
            # Handle different Web3.py versions
            if hasattr(signed_tx, 'rawTransaction'):
                raw_tx = signed_tx.rawTransaction
            elif hasattr(signed_tx, 'raw_transaction'):
                raw_tx = signed_tx.raw_transaction
            else:
                raw_tx = bytes(signed_tx)
            
            # Send transaction
            tx_hash = self.web3.eth.send_raw_transaction(raw_tx)
            
            # Wait for transaction receipt
            receipt = self.web3.eth.wait_for_transaction_receipt(tx_hash)
            
            tx_hash_hex = receipt.transactionHash.hex()
            logger.info(f"Batch transaction successful. {len(asset_ids)} assets processed. Transaction hash: {tx_hash_hex}")
            
            return {
                "success": True,
                "tx_hash": tx_hash_hex,
                "asset_count": len(asset_ids),
                "gas_used": receipt.gasUsed
            }
            
        except Exception as e:
            logger.error(f"Error executing batch transaction: {str(e)}")
            raise HTTPException(status_code=500, detail=f"Batch transaction failed: {str(e)}")
