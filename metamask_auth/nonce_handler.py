from app.core.mongodb_client import MongoDBClient
import random

db_client = MongoDBClient()

def get_nonce(public_address: str) -> int:
    """Fetch nonce for a user, or generate a new one if not found."""
    user = db_client.auth_collection.find_one({"walletAddress": public_address})
    if user and "nonce" in user:
        return user["nonce"]
    return generate_nonce(public_address)

def generate_nonce(public_address: str) -> int:
    """Generates and stores a new nonce for a given public address."""
    nonce = random.randint(100000, 999999)  # Random 6-digit nonce
    db_client.auth_collection.update_one(
        {"walletAddress": public_address},
        {"$set": {"nonce": nonce}},
        upsert=True
    )
    return nonce

def update_nonce(public_address: str):
    """Regenerates a new nonce after successful authentication."""
    new_nonce = random.randint(100000, 999999)
    db_client.auth_collection.update_one(
        {"walletAddress": public_address},
        {"$set": {"nonce": new_nonce}}
    )
