from eth_account.messages import encode_defunct
from web3 import Web3
import os

INFURA_URL = os.getenv("INFURA_URL")
web3 = Web3(Web3.HTTPProvider(INFURA_URL))

def verify_signature(public_address: str, signature: str, nonce: str) -> bool:
    """Verifies if the signature matches the signed nonce."""
    message = encode_defunct(text=f"I am signing my one-time nonce: {nonce}")
    recovered_address = web3.eth.account.recover_message(message, signature=signature)
    return recovered_address.lower() == public_address.lower()