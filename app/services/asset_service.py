from typing import Optional, Dict, Any
from datetime import datetime, timezone
from app.repositories.asset_repo import MongoDBRepository
from app.schemas.asset_schema import (
    AssetCreateRequest,
    AssetUpdateRequest,
    AssetResponse
)
from app.services.ipfs_service import IPFSService
from app.services.blockchain_service import BlockchainService

import logging

logger = logging.getLogger(__name__)

class AssetService:
    def __init__(self):
        self.db_repo = MongoDBRepository()
        self.ipfs_service = IPFSService()
        self.blockchain_service = BlockchainService()

    async def create_asset(self, payload: AssetCreateRequest) -> AssetResponse:
        # Store critical metadata on IPFS
        metadata_cid = await self.ipfs_service.store_metadata({
            "asset_id": payload.asset_id,
            "wallet_address": payload.wallet_address,
            "critical_metadata": payload.critical_metadata
        })

        # Store CID hash on Blockchain
        blockchain_result = await self.blockchain_service.store_cid(metadata_cid)

        # Prepare asset data for MongoDB
        asset_data = {
            "assetId": payload.asset_id,
            "walletAddress": payload.wallet_address,
            "smartContractTxId": blockchain_result.tx_hash,
            "ipfsHash": metadata_cid,
            "criticalMetadata": payload.critical_metadata,
            "nonCriticalMetadata": payload.non_critical_metadata,
            "lastVerified": datetime.now(timezone.utc)
        }

        # Insert asset into MongoDB
        db_repo = MongoDBRepository()
        doc_id = db_repo.insert_asset(asset_data)

        return AssetResponse(
            document_id=doc_id,
            asset_id=payload.asset_id,
            wallet_address=payload.wallet_address,
            version_number=1,
            is_current=True,
            is_deleted=False,
            ipfs_hash=metadata_cid,
            smart_contract_tx_id=blockchain_result.tx_hash,
            last_updated=asset_data["lastVerified"]
        )

    
    async def update_asset(self, payload: AssetUpdateRequest) -> AssetResponse:
        db_repo = MongoDBRepository()
        existing_asset = self.db_repo.find_asset(payload.asset_id)
        
        if not existing_asset:
            raise ValueError("Asset not found")

        # Check if critical metadata changed
        metadata_cid = await self.ipfs_service.store_metadata({
            "asset_id": payload.asset_id,
            "wallet_address": payload.wallet_address,
            "critical_metadata": payload.critical_metadata
        })

        if metadata_cid != existing_asset["ipfsHash"]:
            # Critical metadata changed, store new CID on blockchain
            blockchain_result = await self.blockchain_service.store_hash(metadata_cid)

            new_asset_data = {
                "walletAddress": payload.wallet_address,
                "smartContractTxId": blockchain_result.tx_hash,
                "ipfsHash": metadata_cid,
                "criticalMetadata": payload.critical_metadata,
                "nonCriticalMetadata": payload.non_critical_metadata
            }

            new_version_id = self.db_repo.create_new_version(payload.asset_id, new_asset_data)

            return AssetResponse(
                asset_id=payload.asset_id,
                wallet_address=payload.wallet_address,
                document_id=new_version_id,
                version_number=existing_asset["versionNumber"] + 1,
                is_current=True,
                is_deleted=False,
                ipfs_hash=metadata_cid,
                smart_contract_tx_id=blockchain_result.tx_hash,
                last_updated=datetime.now(timezone.utc)
            )
        else:
            # Only non-critical metadata updated
            updated = self.db_repo.update_noncritical_metadata(
                payload.asset_id, payload.non_critical_metadata
            )

            if not updated:
                raise ValueError("No updates made")

            existing_asset = self.db_repo.find_asset(payload.asset_id)
            
            return AssetResponse(
                asset_id=existing_asset["assetId"],
                wallet_address=existing_asset["walletAddress"],
                document_id=str(existing_asset["_id"]),
                version_number=existing_asset["versionNumber"],
                is_current=True,
                is_deleted=False,
                ipfs_hash=existing_asset["ipfsHash"],
                smart_contract_tx_id=existing_asset["smartContractTxId"],
                last_updated=datetime.now(timezone.utc)
            )
