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

            # Debug the signed_tx object to see what attributes are available
            logger.debug(f"Signed transaction attributes: {dir(signed_tx)}")

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
        Retrieve CID digest from a transaction on the blockchain.
        
        Args:
            tx_hash: Transaction hash to query
            
        Returns:
            Dict containing the retrieved CID information
            
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
                
            # Get the input data from the transaction
            input_data = tx_data['input']
            
            # Decode the input data using the contract ABI
            try:
                # Try to decode the function call and arguments
                func_obj, func_params = self.contract.decode_function_input(input_data)
                
                # Check that this was a call to storeCIDDigest
                if func_obj.function_name != 'storeCIDDigest':
                    raise ValueError(f"Transaction {tx_hash} did not call storeCIDDigest function")
                    
                # Extract the CID from the parameters
                cid = func_params['_cid']
                
                # Calculate the Keccak-256 hash of the CID (this is what the contract does)
                cid_digest = Web3.keccak(text=cid).hex()
                
                logger.info(f"Successfully retrieved CID {cid} from transaction {tx_hash}")
                logger.info(f"Calculated digest: {cid_digest}")
                
                return {
                    "cid": cid,
                    "cid_digest": cid_digest,
                    "tx_hash": tx_hash,
                    "status": "success"
                }
                
            except Exception as decode_error:
                logger.error(f"Error decoding transaction input: {str(decode_error)}")
                
                # Try to get the event logs as an alternative approach
                receipt = self.web3.eth.get_transaction_receipt(tx_hash_bytes)
                
                if receipt and receipt.get('logs'):
                    for log in receipt['logs']:
                        if log['address'].lower() == self.contract_address.lower():
                            # Try to decode the event using the CIDStored event signature
                            try:
                                event_signature = self.contract.events.CIDStored().create_filter(fromBlock='latest').filter_params['topics'][0]
                                if log['topics'][0].hex() == event_signature:
                                    # Extract the digest hash from the event data
                                    # The event has: indexed address user, bytes32 digestHash, uint256 timestamp
                                    # So digestHash is the first 32 bytes of the data
                                    digest_hash = log['data'][:66]  # Take the first 32 bytes (66 chars in hex)
                                    
                                    return {
                                        "cid_digest": digest_hash,
                                        "tx_hash": tx_hash,
                                        "status": "success",
                                        "retrieved_from": "event"
                                    }
                            except Exception as event_error:
                                logger.error(f"Error decoding event: {str(event_error)}")
                
                # If we can't decode the function call or event, try getting CIDs for the sender
                sender = tx_data['from']
                cids = await self.get_cids_for_address(sender)
                
                if cids:
                    # We can't definitely say which CID was stored in this transaction,
                    # but we can return the most recent one as a best guess
                    latest_cid = cids[-1]
                    
                    return {
                        "cid_digest": latest_cid,
                        "tx_hash": tx_hash,
                        "status": "uncertain",
                        "message": "Could not directly decode transaction, returning most recent CID for sender"
                    }
                
                # If all else fails
                raise ValueError(f"Could not retrieve CID from transaction {tx_hash}")
                
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error retrieving hash from transaction: {str(e)}")
            raise HTTPException(
                status_code=500, 
                detail=f"Failed to retrieve hash from transaction: {str(e)}"
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
            # Compute Keccak-256 digest of the given CID (same as what the contract does)
            computed_digest = Web3.keccak(text=cid).hex()
            
            # Get the CID from the blockchain
            blockchain_result = await self.get_hash_from_transaction(tx_hash)
            blockchain_digest = blockchain_result.get("cid_digest")
            
            if not blockchain_digest:
                raise ValueError(f"Could not retrieve CID digest from transaction {tx_hash}")
                
            # Compare digests
            return computed_digest == blockchain_digest
            
        except Exception as e:
            logger.error(f"Error verifying CID: {str(e)}")
            return False
            
    def compute_cid_digest(self, cid: str) -> str:
        """
        Compute the Keccak-256 digest of a CID, matching the contract's implementation.
        
        Args:
            cid: The CID to compute digest for
            
        Returns:
            Hex string of the Keccak-256 digest
        """
        # The contract uses: keccak256(abi.encodePacked(_cid))
        # We need to match this encoding precisely
        try:
            # First try the simple text encoding (most likely case)
            return Web3.keccak(text=cid).hex()
        except Exception:
            # If that fails, try other encodings
            try:
                # Try treating it as hex data
                if cid.startswith('0x'):
                    return Web3.keccak(hexstr=cid).hex()
                else:
                    return Web3.keccak(hexstr='0x' + cid).hex()
            except Exception:
                # Last resort - try raw bytes
                try:
                    return Web3.keccak(primitive=cid.encode('utf-8')).hex()
                except Exception as e:
                    logger.error(f"Failed to compute CID digest: {str(e)}")
                    # Return a placeholder that won't match anything
                    return "0x0000000000000000000000000000000000000000000000000000000000000000"
