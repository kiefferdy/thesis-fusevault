import logging
from fastapi import APIRouter, HTTPException, Query
from typing import Optional
from app.core.mongodb_client import MongoDBClient

router = APIRouter(prefix="/transactions", tags=["transactions"])
db_client = MongoDBClient()

@router.get("/asset/{asset_id}")
async def get_asset_history(asset_id: str, version: Optional[int] = None):
    """
    Get transaction history for a specific asset.
    Optionally filter by version number.
    """
    try:
        query = {"assetId": asset_id}
        
        if version is not None:
            # If version is specified, look for transactions with that version in metadata
            query["$or"] = [
                {"metadata.versionNumber": version},
                {"$and": [{"action": "CREATE"}, {"metadata": {"$exists": False}}]}  # For version 1 without metadata
            ]
        
        transactions = db_client.transaction_collection.find(query).sort("timestamp", -1)
        
        transaction_list = []
        for tx in transactions:
            formatted_tx = {
                "id": str(tx['_id']),
                "action": tx['action'],
                "walletAddress": tx['walletAddress'],
                "timestamp": tx['timestamp'].isoformat(),
                "assetId": tx['assetId']
            }
            
            if 'metadata' in tx:
                formatted_tx['metadata'] = tx['metadata']
                
            transaction_list.append(formatted_tx)
            
        return {"transactions": transaction_list}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/wallet/{wallet_address}")
async def get_wallet_history(wallet_address: str, include_all_versions: bool = False):
    """
    Get transaction history for a specific wallet.
    By default, only includes transactions for current versions unless include_all_versions is True.
    """
    try:
        # First get all current document IDs for this wallet if we're filtering versions
        current_asset_ids = []
        if not include_all_versions:
            documents = db_client.get_documents_by_wallet(wallet_address, include_all_versions=False)
            current_asset_ids = [doc["assetId"] for doc in documents]
            
            # If no documents found, return empty list
            if not current_asset_ids:
                return {"transactions": []}
        
        # Build query
        query = {"walletAddress": wallet_address}
        
        if not include_all_versions and current_asset_ids:
            query["assetId"] = {"$in": current_asset_ids}
            
        transactions = db_client.transaction_collection.find(query).sort("timestamp", -1)
        
        transaction_list = []
        for tx in transactions:
            tx['_id'] = str(tx['_id'])
            tx['timestamp'] = tx['timestamp'].isoformat()
            transaction_list.append(tx)
            
        return {"transactions": transaction_list}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))