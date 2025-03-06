from fastapi import UploadFile, HTTPException, Form
from typing import List, Dict, Any, Optional
from io import StringIO
import json
import pandas as pd
import logging
import os
from dotenv import load_dotenv
from app.services.asset_service import AssetService
from app.utilities.format import format_json, get_ipfs_metadata

logger = logging.getLogger(__name__)

class UploadHandler:
    """
    Handler for file upload operations.
    Processes various types of file uploads (JSON, CSV)
    and direct metadata submissions.
    """

    def __init__(self, asset_service: AssetService = None):
        """Initialize with optional asset service."""
        self.asset_service = asset_service or AssetService()
        load_dotenv()

    async def process_metadata(
        self, 
        asset_id: str,
        wallet_address: str,
        critical_metadata: Dict[str, Any],
        non_critical_metadata: Dict[str, Any],
        file_info: Optional[Dict[str, str]] = None
    ) -> Dict[str, Any]:
        """
        Core function to process metadata for an asset.
        
        - Checks if asset exists
        - Determines if critical metadata has changed using CID comparison
        - Handles IPFS/blockchain if needed
        - Updates MongoDB with new version or creates new document
        
        Args:
            asset_id: The asset's unique identifier
            wallet_address: The wallet address of the owner
            critical_metadata: Core metadata that will be stored on blockchain
            non_critical_metadata: Additional metadata stored only in MongoDB
            file_info: Optional information about source file
            
        Returns:
            Dict with processing results
        """
        try:
            # Check if asset_id already exists
            existing_doc = None
            try:
                existing_doc = await self.asset_service.get_asset(asset_id)
            except Exception as e:
                logger.error(f"Error checking for existing document: {str(e)}")
                result = {"asset_id": asset_id, "status": "error", "detail": f"Error checking for existing document: {str(e)}"}
                if file_info:
                    result.update(file_info)
                return result
            
            # Extract IPFS-relevant metadata
            ipfs_metadata = get_ipfs_metadata({
                "asset_id": asset_id,
                "wallet_address": wallet_address,
                "critical_metadata": critical_metadata
            })
            
            if existing_doc:
                # Document exists, check if critical metadata changed
                existing_ipfs_hash = existing_doc.get("ipfsHash")
                
                # Compute CID for the current metadata
                computed_cid = await self.asset_service.compute_cid(ipfs_metadata)
                
                # If CIDs match, then critical metadata has NOT changed
                critical_metadata_changed = computed_cid != existing_ipfs_hash
                
                if critical_metadata_changed:
                    # Critical metadata changed - upload to IPFS and blockchain
                    # 1) Upload to IPFS
                    cid = await self.asset_service.store_ipfs_metadata(ipfs_metadata)
                    
                    # 2) Store on blockchain
                    blockchain_tx_hash = await self.asset_service.store_blockchain_cid(cid)
                    
                    # 3) Create new version in MongoDB
                    new_doc_id = await self.asset_service.create_new_version(
                        asset_id=asset_id,
                        wallet_address=wallet_address,
                        smart_contract_tx_id=blockchain_tx_hash,
                        ipfs_hash=cid,
                        critical_metadata=critical_metadata,
                        non_critical_metadata=non_critical_metadata
                    )
                    
                    # 4) Get version number of new document
                    new_doc = await self.asset_service.get_asset(asset_id)
                    version_number = new_doc.get("versionNumber", 0)
                    
                    result = {
                        "asset_id": asset_id,
                        "status": "success",
                        "message": "New version created with updated critical metadata",
                        "document_id": new_doc_id,
                        "version": version_number,
                        "ipfs_cid": cid,
                        "blockchain_tx_hash": blockchain_tx_hash,
                    }
                    if file_info:
                        result.update(file_info)
                    return result
                else:
                    # Only non-critical metadata changed - just update MongoDB
                    # Reuse existing IPFS hash and blockchain transaction ID
                    existing_tx_hash = existing_doc.get("smartContractTxId")
                    
                    # Create new version in MongoDB
                    new_doc_id = await self.asset_service.create_new_version(
                        asset_id=asset_id,
                        wallet_address=wallet_address,
                        smart_contract_tx_id=existing_tx_hash,
                        ipfs_hash=existing_ipfs_hash,
                        critical_metadata=critical_metadata,
                        non_critical_metadata=non_critical_metadata
                    )
                    
                    # Get the new version number
                    new_doc = await self.asset_service.get_asset(asset_id)
                    version_number = new_doc.get("versionNumber", 0)
                    
                    result = {
                        "asset_id": asset_id,
                        "status": "success",
                        "message": "New version created with only non-critical metadata updates",
                        "document_id": new_doc_id,
                        "version": version_number,
                        "ipfs_cid": existing_ipfs_hash,
                        "blockchain_tx_hash": existing_tx_hash,
                    }
                    if file_info:
                        result.update(file_info)
                    return result
            else:
                # New document - proceed with normal flow
                # 1) Upload to IPFS
                cid = await self.asset_service.store_ipfs_metadata(ipfs_metadata)
                
                # 2) Store on blockchain
                blockchain_tx_hash = await self.asset_service.store_blockchain_cid(cid)
                
                # 3) Insert into MongoDB
                doc_id = await self.asset_service.create_asset(
                    asset_id=asset_id,
                    wallet_address=wallet_address,
                    smart_contract_tx_id=blockchain_tx_hash,
                    ipfs_hash=cid,
                    critical_metadata=critical_metadata,
                    non_critical_metadata=non_critical_metadata
                )
                
                result = {
                    "asset_id": asset_id,
                    "status": "success",
                    "message": "Document created",
                    "document_id": doc_id,
                    "version": 1,
                    "ipfs_cid": cid,
                    "blockchain_tx_hash": blockchain_tx_hash,
                }
                if file_info:
                    result.update(file_info)
                return result
                
        except Exception as e:
            logger.error(f"Error processing metadata for asset {asset_id}: {str(e)}")
            result = {"asset_id": asset_id, "status": "error", "detail": f"Error processing metadata: {str(e)}"}
            if file_info:
                result.update(file_info)
            return result

    async def handle_metadata_upload(
        self,
        asset_id: str,
        wallet_address: str,
        critical_metadata: str,
        non_critical_metadata: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Upload metadata directly (not as a file).
        
        - Takes asset_id, wallet_address, and metadata as parameters
        - Checks if critical metadata has changed using CID comparison
        - Stores in IPFS only if changed
        - Registers on blockchain only if changed
        - Updates MongoDB
        
        Args:
            asset_id: The asset's unique identifier
            wallet_address: The wallet address of the owner
            critical_metadata: JSON string of core metadata
            non_critical_metadata: JSON string of additional metadata
            
        Returns:
            Dict with processing results
        """
        try:
            # Parse JSON strings
            critical_md = json.loads(critical_metadata)
            non_critical_md = json.loads(non_critical_metadata) if non_critical_metadata else {}
            
            # Process metadata
            return await self.process_metadata(
                asset_id=asset_id,
                wallet_address=wallet_address,
                critical_metadata=critical_md,
                non_critical_metadata=non_critical_md
            )
                
        except json.JSONDecodeError as e:
            logger.error(f"Invalid JSON format: {str(e)}")
            return {"asset_id": asset_id, "status": "error", "detail": f"Invalid JSON format: {str(e)}"}
        except Exception as e:
            logger.error(f"Error processing metadata: {str(e)}")
            return {"asset_id": asset_id, "status": "error", "detail": f"Error processing metadata: {str(e)}"}

    async def handle_json_files(
        self, 
        files: List[UploadFile], 
        wallet_address: str
    ) -> Dict[str, Any]:
        """
        Process JSON files uploaded by the user.
        
        - Each JSON file must have: asset_id, critical_metadata, optional non_critical_metadata
        - Each file represents a single document/asset
        - Duplicate asset_ids are skipped (first occurrence is used)
        
        Args:
            files: List of uploaded JSON files
            wallet_address: The wallet address of the owner
            
        Returns:
            Dict with processing results for each file
        """
        seen_asset_ids = set()
        results = []
        
        for file_obj in files:
            if not file_obj.filename.lower().endswith(".json"):
                results.append({
                    "filename": file_obj.filename,
                    "status": "error",
                    "detail": "Not a JSON file. Use .json extension."
                })
                continue
                
            try:
                content = await file_obj.read()
                try:
                    data = json.loads(content.decode("utf-8"))
                except Exception as e:
                    results.append({
                        "filename": file_obj.filename,
                        "status": "error",
                        "detail": f"Invalid JSON file: {str(e)}"
                    })
                    continue
                
                # Check required fields
                asset_id = data.get("asset_id")
                critical_metadata = data.get("critical_metadata")
                non_critical_metadata = data.get("non_critical_metadata", {})
                
                if not asset_id or not critical_metadata:
                    results.append({
                        "filename": file_obj.filename,
                        "status": "error",
                        "detail": "Missing 'asset_id' or 'critical_metadata' in JSON."
                    })
                    continue
                
                # If we have not seen asset_id, proceed; else skip
                if asset_id in seen_asset_ids:
                    results.append({
                        "asset_id": asset_id,
                        "filename": file_obj.filename,
                        "status": "skipped",
                        "detail": "Duplicate asset_id; ignoring subsequent file."
                    })
                    continue
                
                # Mark it as seen
                seen_asset_ids.add(asset_id)
                
                # Process metadata with file info
                result = await self.process_metadata(
                    asset_id=asset_id,
                    wallet_address=wallet_address,
                    critical_metadata=critical_metadata,
                    non_critical_metadata=non_critical_metadata,
                    file_info={"filename": file_obj.filename}
                )
                
                results.append(result)
                    
            except Exception as e:
                results.append({
                    "filename": file_obj.filename,
                    "status": "error",
                    "detail": f"Error processing file: {str(e)}"
                })
        
        return {
            "upload_count": len(results),
            "results": results
        }

    async def process_csv_upload(
        self,
        files: List[UploadFile],
        wallet_address: str,
        critical_metadata_fields: List[str]
    ) -> Dict[str, Any]:
        """
        Process CSV files uploaded by the user.
        
        - Each row in the CSV is treated as a distinct record with a unique asset_id
        - Must supply 'critical_metadata_fields' to identify which columns are critical
        - Each row must have an 'asset_id' column
        - Duplicate asset_ids are skipped (first occurrence is used)
        
        Args:
            files: List of uploaded CSV files
            wallet_address: The wallet address of the owner
            critical_metadata_fields: List of column names to treat as critical metadata
            
        Returns:
            Dict with processing results for each file
        """
        seen_asset_ids = set()
        results = []
        
        # Helper to parse CSV rows into document dictionaries
        def parse_csv(file_content: bytes, critical_fields: List[str]) -> List[Dict[str, Any]]:
            """Parse CSV bytes into a list of asset dictionaries."""
            csv_df = pd.read_csv(StringIO(file_content.decode("utf-8")))

            if "asset_id" not in csv_df.columns:
                raise ValueError("CSV file must contain an 'asset_id' column.")

            # Ensure critical fields exist
            missing = [col for col in critical_fields if col not in csv_df.columns]
            if missing:
                raise ValueError(f"Missing critical columns {missing} in CSV.")

            records = []
            for _, row in csv_df.iterrows():
                row_dict = row.to_dict()

                asset_id = str(row_dict["asset_id"])
                critical_md = {c: row_dict[c] for c in critical_fields}
                # Everything else is non-critical (besides asset_id)
                non_critical_md = {
                    k: v for k, v in row_dict.items()
                    if k not in critical_fields and k != "asset_id"
                }
                records.append({
                    "asset_id": asset_id,
                    "critical_metadata": critical_md,
                    "non_critical_metadata": non_critical_md
                })
            return records
        
        for file_obj in files:
            if not file_obj.filename.lower().endswith(".csv"):
                results.append({
                    "filename": file_obj.filename,
                    "status": "error",
                    "detail": "Not a CSV file. Use .csv extension."
                })
                continue
                
            try:
                content = await file_obj.read()
                try:
                    row_docs = parse_csv(content, critical_metadata_fields)
                except Exception as e:
                    results.append({
                        "filename": file_obj.filename,
                        "status": "error",
                        "detail": f"CSV parse error: {str(e)}"
                    })
                    continue
                
                # Process each row as a separate document
                for row_doc in row_docs:
                    asset_id = row_doc["asset_id"]
                    
                    # Check for duplicates
                    if asset_id in seen_asset_ids:
                        results.append({
                            "asset_id": asset_id,
                            "filename": file_obj.filename,
                            "status": "skipped",
                            "detail": "Duplicate asset_id found in CSV; ignoring this row."
                        })
                        continue
                    
                    seen_asset_ids.add(asset_id)
                    
                    # Process metadata with file info
                    result = await self.process_metadata(
                        asset_id=asset_id,
                        wallet_address=wallet_address,
                        critical_metadata=row_doc["critical_metadata"],
                        non_critical_metadata=row_doc["non_critical_metadata"],
                        file_info={"filename": file_obj.filename}
                    )
                    
                    results.append(result)
                    
            except Exception as e:
                results.append({
                    "filename": file_obj.filename,
                    "status": "error",
                    "detail": f"Error processing file: {str(e)}"
                })
        
        return {
            "upload_count": len(results),
            "results": results
        }
