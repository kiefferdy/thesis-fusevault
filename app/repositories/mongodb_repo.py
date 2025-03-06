# repositories/mongodb_repo.py

from typing import Dict, Any, List, Optional
from datetime import datetime, timezone
from pymongo import MongoClient, DESCENDING
from bson import ObjectId
from dotenv import load_dotenv
import logging
import os

logger = logging.getLogger(__name__)


class MongoDBRepository:
    def __init__(self):
        load_dotenv()
        self.mongo_uri = os.getenv("MONGO_URI")

        self.client = MongoClient(self.mongo_uri)
        self.db = self.client["fusevault"]
        self.assets = self.db["assets"]
        self.transactions = self.db["transactions"]

    def insert_asset(self, asset_data: Dict[str, Any]) -> str:
        asset_data.update({
            "versionNumber": 1,
            "isCurrent": True,
            "isDeleted": False,
            "lastUpdated": datetime.now(timezone.utc),
            "lastVerified": datetime.now(timezone.utc),
            "documentHistory": []
        })
        result = self.assets.insert_one(asset_data)
        self.record_transaction(asset_data["assetId"], "CREATE", asset_data["walletAddress"])
        return str(result.inserted_id)

    def find_asset(self, asset_id: str, version: Optional[int] = None) -> Optional[Dict[str, Any]]:
        query = {"assetId": asset_id, "isDeleted": False}
        if version:
            query["versionNumber"] = version
        else:
            query["isCurrent"] = True

        asset = self.assets.find_one(query)
        if asset:
            asset["_id"] = str(asset["_id"])
        return asset

    def find_assets_by_wallet(self, wallet_address: str, include_all_versions: bool = False) -> List[Dict[str, Any]]:
        query = {"walletAddress": wallet_address, "isDeleted": False}
        if not include_all_versions:
            query["isCurrent"] = True

        assets = list(self.assets.find(query).sort("lastUpdated", DESCENDING))
        for asset in assets:
            asset["_id"] = str(asset["_id"])
        return assets

    def create_asset_version(self, asset_id: str, new_asset_data: Dict[str, Any]) -> str:
        current_asset = self.assets.find_one({"assetId": asset_id, "isCurrent": True})
        if not current_asset:
            raise ValueError("Asset not found")

        # Mark current asset as not current
        self.assets.update_one(
            {"_id": current_asset["_id"]},
            {"$set": {"isCurrent": False}}
        )

        new_asset_data.update({
            "versionNumber": current_asset["versionNumber"] + 1,
            "previousVersionId": str(current_asset["_id"]),
            "documentHistory": current_asset.get("documentHistory", []) + [str(current_asset["_id"])],
            "isCurrent": True,
            "isDeleted": False,
            "lastUpdated": datetime.now(timezone.utc),
            "lastVerified": datetime.now(timezone.utc)
        })

        result = self.assets.insert_one(new_asset_data)
        self.record_transaction(asset_id, "VERSION_CREATE", new_asset_data["walletAddress"], {
            "previousVersionId": str(current_asset["_id"]),
            "versionNumber": new_asset_data["versionNumber"]
        })

        return str(result.inserted_id)

    def update_noncritical_metadata(self, asset_id: str, metadata: Dict[str, Any]) -> bool:
        result = self.assets.update_one(
            {"assetId": asset_id, "isCurrent": True},
            {"$set": {
                "nonCriticalMetadata": metadata,
                "lastUpdated": datetime.now(timezone.utc)
            }}
        )
        return result.modified_count > 0

    def soft_delete_asset(self, asset_id: str, deleted_by: str) -> bool:
        result = self.assets.update_one(
            {"assetId": asset_id, "isCurrent": True},
            {"$set": {
                "isDeleted": True,
                "deletedBy": deleted_by,
                "deletedAt": datetime.now(timezone.utc)
            }}
        )
        if result.modified_count > 0:
            self.record_transaction(asset_id, "DELETE", deleted_by)
            return True
        return False

    def record_transaction(self, asset_id: str, action: str, wallet_address: str, metadata: dict = None) -> str:
        transaction_data = {
            "assetId": asset_id,
            "action": action,
            "walletAddress": wallet_address,
            "timestamp": datetime.now(timezone.utc)
        }
        if metadata:
            transaction_data["metadata"] = metadata

        result = self.transactions.insert_one(transaction_data)
        return str(result.inserted_id)

    def fetch_transaction_history(self, asset_id: str) -> List[Dict[str, Any]]:
        transactions = list(self.transactions.find({"assetId": asset_id}).sort("timestamp", DESCENDING))
        for tx in transactions:
            tx["_id"] = str(tx["_id"])
        return transactions

    def close_connection(self):
        self.client.close()
