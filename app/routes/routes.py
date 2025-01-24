from fastapi import APIRouter

router = APIRouter()

@router.get("/",
            description="This is the documentation description text for '/' path GET operation.")
async def index():
    return {"message": "Welcome to FuseVault!"}

@router.get("/ping/{pong_str}",
            description="This is the documentation description text for '/ping' path GET operation.")
async def ping(pong_str):
    return {"message": pong_str}


# smart contracts
from fastapi import APIRouter, HTTPException
from web3 import Web3
import os

# Load environment variables
from dotenv import load_dotenv
load_dotenv()

router = APIRouter()

# Initialize Web3
w3 = Web3(Web3.HTTPProvider(os.getenv("WEB3_PROVIDER_URL")))  # Replace with your provider URL
contract_address = os.getenv("CONTRACT_ADDRESS")
contract_abi = [
    {
        "inputs": [{"internalType": "string", "name": "cid", "type": "string"}],
        "name": "storeCIDDigest",
        "outputs": [],
        "stateMutability": "nonpayable",
        "type": "function"
    },
    # Add more ABI methods here if needed
]

# Set up the contract instance
contract = w3.eth.contract(address=contract_address, abi=contract_abi)

# Define route to store CID
@router.post("/store_cid")
async def store_cid(cid: str):
    try:
        # Get the first account (or change to a specific address)
        account = w3.eth.accounts[0]
        # Build the transaction to store the CID
        tx = contract.functions.storeCIDDigest(cid).buildTransaction({
            'from': account,
            'gas': 2000000,
            'gasPrice': w3.toWei('20', 'gwei'),
            'nonce': w3.eth.getTransactionCount(account),
        })

        # Sign the transaction (you need to provide the private key here)
        private_key = os.getenv("PRIVATE_KEY")  # Make sure to set the private key in your .env file
        signed_tx = w3.eth.account.signTransaction(tx, private_key)

        # Send the transaction
        tx_hash = w3.eth.sendRawTransaction(signed_tx.rawTransaction)

        return {"tx_hash": tx_hash.hex()}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


# Define route to fetch stored CID digest hash by address
@router.get("/fetch_cid/{user_address}")
async def fetch_cid(user_address: str):
    try:
        # Fetch the CID digest by the user address
        cids = contract.functions.fetchCIDsDigestByAddress(user_address).call()
        return {"cids": cids}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))