import os
import logging
from web3 import Web3
from dotenv import load_dotenv
from typing import Any, Dict, Optional, List
from fastapi import HTTPException

logger = logging.getLogger(__name__)

class BlockchainService:
    def __init__(self):
        load_dotenv()
        self.infura_url = os.getenv("INFURA_URL")
        self.wallet_address = os.getenv("WALLET_ADDRESS")
        self.private_key = os.getenv("PRIVATE_KEY")
        self.contract_address = os.getenv("CONTRACT_ADDRESS")
        self.contract_abi = [
            {
                "inputs": [{"internalType": "string", "name": "_cid", "type": "string"}],
                "name": "storeCIDDigest",
                "outputs": [],
                "stateMutability": "nonpayable",
                "type": "function"
            },
            {
                "inputs": [{"internalType": "address", "name": "user", "type": "address"}],
                "name": "fetchCIDsDigestByAddress",
                "outputs": [{"internalType": "bytes32[]", "name": "digestHashes", "type": "bytes32[]"}],
                "stateMutability": "view",
                "type": "function"
            },
            {
                "inputs": [],
                "name": "fetchMyCIDsDigest",
                "outputs": [{"internalType": "bytes32[]", "name": "digestHashes", "type": "bytes32[]"}],
                "stateMutability": "view",
                "type": "function"
            },
            {
                "anonymous": False,
                "inputs": [
                    {"indexed": True, "internalType": "address", "name": "user", "type": "address"},
                    {"indexed": False, "internalType": "bytes32", "name": "digestHash", "type": "bytes32"},
                    {"indexed": False, "internalType": "uint256", "name": "timestamp", "type": "uint256"}
                ],
                "name": "CIDStored",
                "type": "event"
            }
        ]

        self.web3 = Web3(Web3.HTTPProvider(self.infura_url))

        if not self.web3.is_connected():
            logger.error("Unable to connect to Infura.")
            raise HTTPException(status_code=500, detail="Blockchain connection error")

        try:
            self.contract = self.web3.eth.contract(
                address=Web3.to_checksum_address(self.contract_address),
                abi=self.contract_abi
            )
        except Exception as e:
            logger.error(f"Error setting up contract: {str(e)}")
            raise

    async def store_hash(self, cid: str) -> Dict[str, Any]:
        try:
            # Build transaction
            nonce = self.web3.eth.get_transaction_count(self.wallet_address)
            tx = self.contract.functions.storeCIDDigest(cid).build_transaction({
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
                try:
                    # Try to extract the raw transaction data in other ways
                    if hasattr(signed_tx, '__dict__'):
                        for key, value in signed_tx.__dict__.items():
                            if isinstance(value, (bytes, bytearray)):
                                raw_tx = value
                                break
                    # If we can't find any bytes attribute, convert the entire object to bytes
                    raw_tx = bytes(signed_tx)
                except:
                    raise ValueError("Could not extract raw transaction bytes. "
                                    "Check Web3.py version compatibility.")

            # Send transaction
            tx_hash = self.web3.eth.send_raw_transaction(raw_tx)

            # Wait for transaction receipt
            receipt = self.web3.eth.wait_for_transaction_receipt(tx_hash)

            logger.info(f"CID successfully stored on blockchain. Transaction hash: {receipt.transactionHash.hex()}")

            return {"tx_hash": receipt.transactionHash.hex()}

        except Exception as e:
            logger.error(f"Blockchain error: {str(e)}")
            raise HTTPException(status_code=500, detail=f"Blockchain transaction failed: {str(e)}")

    async def get_hash_from_transaction(self, tx_hash: str) -> Dict[str, Any]:
        """
        Retrieve CID from a transaction on the blockchain.
        
        Args:
            tx_hash: Transaction hash to query
            
        Returns:
            Dict containing the retrieved CID information and transaction sender
            
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
            
            # Decode the input data using the contract ABI
            try:
                # Try to decode the function call and arguments
                func_obj, func_params = self.contract.decode_function_input(input_data)
                
                # Check that this was a call to storeCIDDigest
                if func_obj.fn_name != 'storeCIDDigest':
                    raise ValueError(f"Transaction {tx_hash} did not call storeCIDDigest function")
                    
                # Extract the CID from the parameters
                cid = func_params['_cid']
                
                logger.info(f"Successfully retrieved CID {cid} from transaction {tx_hash}")
                
                # Ensure tx_sender is properly formatted and always included
                if tx_sender:
                    tx_sender = tx_sender.lower()
                
                logger.info(f"Transaction sender for tx {tx_hash}: {tx_sender}")
                
                return {
                    "cid": cid,
                    "tx_hash": tx_hash,
                    "tx_sender": tx_sender,
                    "status": "success"
                }
                
            except Exception as decode_error:
                logger.error(f"Error decoding transaction input: {str(decode_error)}")
                raise ValueError(f"Could not retrieve CID from blockchain transaction {tx_hash}")
                
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error retrieving CID from transaction: {str(e)}")
            raise HTTPException(
                status_code=500, 
                detail=f"Failed to retrieve CID from blockchain transaction: {str(e)}"
            )
            
    async def get_cids_for_address(self, address: str) -> List[str]:
        """
        Get all CID digests stored by a specific address.
        
        Args:
            address: The address to query
            
        Returns:
            List of CID digests stored by the address
        """
        try:
            # Call the fetchCIDsDigestByAddress function on the contract
            digest_hashes = self.contract.functions.fetchCIDsDigestByAddress(
                Web3.to_checksum_address(address)
            ).call()
            
            # Convert bytes32 hashes to hex strings
            return [hash.hex() for hash in digest_hashes if hash != b'\x00' * 32]
            
        except Exception as e:
            logger.error(f"Error getting CIDs for address {address}: {str(e)}")
            return []
            
    async def verify_cid(self, cid: str, tx_hash: str) -> bool:
        """
        Verify if a given CID matches what was stored in a specific transaction.
        
        Args:
            cid: The CID to verify
            tx_hash: Transaction hash where the CID was stored
            
        Returns:
            True if CID matches the one in the transaction, False otherwise
        """
        try:
            # Get the CID from the blockchain
            blockchain_result = await self.get_hash_from_transaction(tx_hash)
            blockchain_cid = blockchain_result.get("cid")
            
            if not blockchain_cid:
                raise ValueError(f"Could not retrieve CID from transaction {tx_hash}")
                
            # Direct CID comparison
            return cid == blockchain_cid
            
        except Exception as e:
            logger.error(f"Error verifying CID: {str(e)}")
            return False
            
    def get_server_wallet_address(self) -> str:
        """
        Get the server's wallet address used for signing transactions.
        
        Returns:
            Server wallet address
        """
        return self.wallet_address
