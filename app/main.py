from fastapi import FastAPI, HTTPException
from web3 import Web3
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Initialize FastAPI app
app = FastAPI()

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

# Contract ABI (example ABI based on provided JSON)
CONTRACT_ABI = [
    {
        "inputs": [{"internalType": "string", "name": "cid", "type": "string"}],
        "name": "storeCIDDigest",
        "outputs": [],
        "stateMutability": "nonpayable",
        "type": "function",
    },
    {
        "inputs": [{"internalType": "address", "name": "user", "type": "address"}],
        "name": "fetchCIDsDigestByAddress",
        "outputs": [{"internalType": "bytes32[]", "name": "digestHashes", "type": "bytes32[]"}],
        "stateMutability": "view",
        "type": "function",
    },
    {
        "inputs": [],
        "name": "fetchMyCIDsDigest",
        "outputs": [{"internalType": "bytes32[]", "name": "digestHashes", "type": "bytes32[]"}],
        "stateMutability": "view",
        "type": "function",
    },
]

# Initialize contract
contract = web3.eth.contract(address=CONTRACT_ADDRESS, abi=CONTRACT_ABI)

@app.post("/store_cid/")
async def store_cid(cid: str):
    try:
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

        # Skip MongoDB insertion, just return the response with the transaction hash
        return {
            "cid": cid,
            "blockchain_tx": receipt.transactionHash.hex(),
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/fetch_cids/")
async def fetch_cids(user_address: str):
    try:
        # Convert user_address to checksum format
        user_address = Web3.to_checksum_address(user_address)
        cids = contract.functions.fetchCIDsDigestByAddress(user_address).call()
        return {"user_address": user_address, "cids": cids}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/fetch_my_cids/")
async def fetch_my_cids():
    try:
        cids = contract.functions.fetchMyCIDsDigest().call()
        return {"cids": cids}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
