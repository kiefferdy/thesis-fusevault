import os
import logging
from web3 import Web3
from dotenv import load_dotenv
from typing import Any, Dict
from fastapi import HTTPException

logger = logging.getLogger(__name__)

class BlockchainService:
    def __init__(self):
        load_dotenv()
        self.provider_url = os.getenv("ALCHEMY_SEPOLIA_URL")
        self.wallet_address = os.getenv("WALLET_ADDRESS")
        self.private_key = os.getenv("PRIVATE_KEY")
        self.contract_address = os.getenv("CONTRACT_ADDRESS")
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
        except Exception as e:
            logger.error(f"Error setting up contract: {str(e)}")
            raise

    async def store_hash(self, cid: str, asset_id: str) -> Dict[str, Any]:
        """
        Store a CID hash on the blockchain for a specific asset.
        
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

    async def store_hash_for(self, cid: str, asset_id: str, owner_address: str) -> Dict[str, Any]:
        """
        Store a CID hash on the blockchain for a specific asset on behalf of another owner.
        
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

    async def delete_asset(self, asset_id: str) -> Dict[str, Any]:
        """
        Mark an asset as deleted on the blockchain.
        
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

    async def delete_asset_for(self, asset_id: str, owner_address: str) -> Dict[str, Any]:
        """
        Mark an asset as deleted on the blockchain on behalf of another owner.
        
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

    async def get_transaction_details(self, tx_hash: str) -> Dict[str, Any]:
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
            
    def get_server_wallet_address(self) -> str:
        """
        Get the server's wallet address used for signing transactions.
        
        Returns:
            Server wallet address
        """
        return self.wallet_address
