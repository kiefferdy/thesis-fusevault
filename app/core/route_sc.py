import hashlib
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel  # ✅ Import Pydantic model for validation
from web3 import Web3
import os
from dotenv import load_dotenv
import logging

# Set the default logging level to INFO (so your own logs still appear)
logging.basicConfig(level=logging.INFO)

# Suppress noisy logs from specific libraries
logging.getLogger("uvicorn.errors").setLevel(logging.WARNING)  # Hide Uvicorn request logs
# Load environment variables
load_dotenv()

router = APIRouter()

# Blockchain setup
INFURA_URL = os.getenv("INFURA_URL")
if not INFURA_URL:
    raise HTTPException(status_code=500, detail="Infura URL is missing in the environment variables")

web3 = Web3(Web3.HTTPProvider(INFURA_URL))
if not web3.is_connected():
    raise HTTPException(status_code=500, detail="Failed to connect to Infura")

# Contract setup
raw_contract_address = os.getenv("CONTRACT_ADDRESS")
if not raw_contract_address:
    raise HTTPException(status_code=500, detail="Contract address is missing in the environment variables")

# Convert to checksum address
try:
    CONTRACT_ADDRESS = Web3.to_checksum_address(raw_contract_address)
except ValueError:
    raise HTTPException(status_code=500, detail="Invalid contract address format")

# Contract ABI
CONTRACT_ABI = [
    {
        "inputs": [{"internalType": "string", "name": "cid", "type": "string"}],
        "name": "storeCIDDigest",
        "outputs": [],
        "stateMutability": "nonpayable",
        "type": "function",
    }
]

# Initialize contract
contract = web3.eth.contract(address=CONTRACT_ADDRESS, abi=CONTRACT_ABI)

# ✅ Define a Pydantic model for the request body
class CIDRequest(BaseModel):
    cid: str

@router.post("/store_cid/")
async def store_cid(payload: CIDRequest):
    try:
        cid = payload.cid  # Extract CID from the validated request

        # Compute SHA-256 encoded hash
        sha256_hash = hashlib.sha256(cid.encode()).hexdigest()

        # Retrieve blockchain credentials
        sender_address = os.getenv("WALLET_ADDRESS")
        private_key = os.getenv("PRIVATE_KEY")

        if not sender_address or not private_key:
            raise HTTPException(status_code=500, detail="Missing blockchain credentials in environment variables")

        # Ensure private key has '0x' prefix
        if not private_key.startswith("0x"):
            private_key = "0x" + private_key

        # Build the transaction
        nonce = web3.eth.get_transaction_count(sender_address)
        gas_price = web3.eth.gas_price

        transaction = contract.functions.storeCIDDigest(cid).build_transaction({
            "from": Web3.to_checksum_address(sender_address),
            "nonce": nonce,
            "gas": 2000000,
            "gasPrice": gas_price,
        })

        # Sign the transaction
        signed_tx = web3.eth.account.sign_transaction(transaction, private_key)

        # Send the transaction
        tx_hash = web3.eth.send_raw_transaction(signed_tx.raw_transaction)

        # Wait for transaction receipt
        receipt = web3.eth.wait_for_transaction_receipt(tx_hash)

        # Extract the blockchain transaction hash
        blockchain_tx_hash = receipt.transactionHash.hex()

        # ✅ Print the result in terminal
        print("\n✅ CID Successfully Stored on Blockchain!\n")
        print(f"CID: {cid}\n")
        print(f"Encoded Hash (SHA-256): {sha256_hash}\n")
        print(f"Transaction Hash: {blockchain_tx_hash}\n")

        return {
            "cid": cid,
            "encoded_hash": sha256_hash,
            "tx_hash": blockchain_tx_hash,
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))