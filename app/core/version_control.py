from datetime import datetime, timezone
from typing import Dict, Any, List, Optional
from bson import ObjectId

class VersionControl:
    def __init__(self, db_client):
        self.db_client = db_client
        self.domain_collection = db_client.domain_collection
        
    async def create_new_version(
        self,
        document_id: str,
        smart_contract_tx_id: str,
        ipfs_hash: str,
        critical_metadata: Dict[str, Any],
        non_critical_metadata: Dict[str, Any],
        user_wallet_address: str
    ) -> str:
        """
        Creates a new version of a document while preserving the version history.
        Returns the new document ID.
        """
        # Get the current document
        current_doc = self.domain_collection.find_one({"_id": ObjectId(document_id)})
        if not current_doc:
            raise ValueError(f"Document {document_id} not found")
            
        # Mark the current version as not current
        self.domain_collection.update_one(
            {"_id": ObjectId(document_id)},
            {"$set": {"isCurrent": False}}
        )
        
        # Create new version document
        new_doc = {
            "assetId": current_doc["assetId"],
            "userWalletAddress": user_wallet_address,
            "smartContractTxId": smart_contract_tx_id,
            "ipfsHash": ipfs_hash,
            "lastVerified": datetime.now(timezone.utc),
            "lastUpdated": datetime.now(timezone.utc),
            "criticalMetadata": critical_metadata,
            "nonCriticalMetadata": non_critical_metadata,
            "isCurrent": True,
            "isDeleted": False,
            "documentHistory": [*current_doc.get("documentHistory", []), str(current_doc["_id"])],
            "version": current_doc.get("version", 1) + 1,
            "previousVersion": str(current_doc["_id"])
        }
        
        # Insert new version
        result = self.domain_collection.insert_one(new_doc)
        new_doc_id = str(result.inserted_id)
        
        # Record the version creation in transaction history
        self.db_client._record_transaction(
            document_id=new_doc_id,
            action="VERSION_CREATE",
            wallet_address=user_wallet_address,
            metadata={
                "previousVersion": document_id,
                "version": new_doc["version"]
            }
        )
        
        return new_doc_id
        
    async def get_version_history(self, asset_id: str) -> List[Dict[str, Any]]:
        """
        Retrieves the complete version history for an asset.
        Returns list of versions ordered from newest to oldest.
        """
        # Find all documents with this asset_id
        versions = self.domain_collection.find(
            {"assetId": asset_id}
        ).sort("version", -1)
        
        version_list = []
        for version in versions:
            version_info = {
                "documentId": str(version["_id"]),
                "version": version.get("version", 1),
                "timestamp": version["lastUpdated"],
                "ipfsHash": version["ipfsHash"],
                "smartContractTxId": version["smartContractTxId"],
                "isCurrent": version["isCurrent"]
            }
            version_list.append(version_info)
            
        return version_list
        
    async def get_specific_version(
        self,
        asset_id: str,
        version_number: int
    ) -> Optional[Dict[str, Any]]:
        """
        Retrieves a specific version of a document.
        """
        version_doc = self.domain_collection.find_one({
            "assetId": asset_id,
            "version": version_number
        })
        
        if version_doc:
            version_doc["_id"] = str(version_doc["_id"])
            return version_doc
        return None
        
    async def compare_versions(
        self,
        asset_id: str,
        version1: int,
        version2: int
    ) -> Dict[str, Any]:
        """
        Compares two versions of a document and returns the differences.
        """
        v1_doc = await self.get_specific_version(asset_id, version1)
        v2_doc = await self.get_specific_version(asset_id, version2)
        
        if not v1_doc or not v2_doc:
            raise ValueError("One or both versions not found")
            
        differences = {
            "criticalMetadata": self._compare_metadata(
                v1_doc["criticalMetadata"],
                v2_doc["criticalMetadata"]
            ),
            "nonCriticalMetadata": self._compare_metadata(
                v1_doc["nonCriticalMetadata"],
                v2_doc["nonCriticalMetadata"]
            ),
            "ipfsHash": {
                "changed": v1_doc["ipfsHash"] != v2_doc["ipfsHash"],
                "v1": v1_doc["ipfsHash"],
                "v2": v2_doc["ipfsHash"]
            }
        }
        
        return differences
        
    def _compare_metadata(
        self,
        metadata1: Dict[str, Any],
        metadata2: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Helper method to compare metadata dictionaries and identify changes.
        """
        all_keys = set(metadata1.keys()) | set(metadata2.keys())
        differences = {}
        
        for key in all_keys:
            value1 = metadata1.get(key)
            value2 = metadata2.get(key)
            
            if value1 != value2:
                differences[key] = {
                    "v1": value1,
                    "v2": value2
                }
                
        return differences