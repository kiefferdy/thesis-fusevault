from fastapi import APIRouter, HTTPException
from web3 import Web3
import os
from dotenv import load_dotenv

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
    {
        "anonymous": False,
        "inputs": [
            {"indexed": True, "internalType": "address", "name": "user", "type": "address"},
            {"indexed": False, "internalType": "bytes32", "name": "digestHash", "type": "bytes32"},
            {"indexed": False, "internalType": "uint256", "name": "timestamp", "type": "uint256"},
        ],
        "name": "CIDStored",
        "type": "event",
    },
]

# Initialize contract
contract = web3.eth.contract(address=CONTRACT_ADDRESS, abi=CONTRACT_ABI)

@router.post("/store_cid/")
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

@router.get("/fetch_cids/")
async def fetch_cids(user_address: str):
    try:
        # Convert user_address to checksum format
        user_address = Web3.to_checksum_address(user_address)
        cids = contract.functions.fetchCIDsDigestByAddress(user_address).call()
        formatted_cids = []
        for cid in cids:
            if isinstance(cid, bytes):
                formatted_cids.append(cid.hex())  # Convert bytes to hexadecimal string
            else:
                formatted_cids.append(cid)  # Leave as is if not bytes

        return {"user_address": user_address, "cids": formatted_cids}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/fetch_my_cids/")
async def fetch_my_cids():
    try:
        cids = contract.functions.fetchMyCIDsDigest().call()
        return {"cids": cids}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/fetch_cid_by_tx_hash/")
async def fetch_cid_by_tx_hash(tx_hash: str):
    try:
        # Fetch the transaction receipt using the transaction hash
        receipt = web3.eth.get_transaction_receipt(tx_hash)

        if not receipt:
            raise HTTPException(status_code=404, detail="Transaction receipt not found")

        # Loop through the logs to find the CIDStored event
        for log in receipt['logs']:
            if log['address'].lower() == CONTRACT_ADDRESS.lower():
                try:
                    # Manually decode the event log data (data field contains the encoded data)
                    data = log['data'].hex()  # Convert HexBytes to hex string
                    topics = log['topics']

                    # Decode the address (indexed)
                    user_address = '0x' + topics[1].hex()[26:]  # Remove leading zeros and prepend '0x'

                    # Decode the CID (non-indexed)
                    cid = bytes.fromhex(data[2:66])  # Convert hex string to bytes, skipping the '0x' prefix

                    # Decode the timestamp (non-indexed)
                    timestamp = int(data[66:130], 16)  # timestamp is in the data after the cid

                    return {
                        "transaction_hash": tx_hash,
                        "user_address": user_address,
                        "encoded_cid": cid.hex(),  # Return the CID as a hexadecimal string
                        "timestamp": timestamp,
                    }

                except Exception as e:
                    # Handle potential errors in decoding
                    raise HTTPException(status_code=500, detail=f"Error decoding event log: {str(e)}")

        # If no CID was found in the logs
        raise HTTPException(status_code=404, detail="CID not found in the transaction logs")

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error: {str(e)}")
