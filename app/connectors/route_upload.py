from fastapi import APIRouter, HTTPException, UploadFile, File, Form, Query
from typing import List, Dict, Any, Optional
from io import BytesIO, StringIO
import pandas as pd
import json
import logging
import os
from dotenv import load_dotenv

from app.core.mongodb_client import MongoDBClient
from app.core.route_sc import store_cid as blockchain_store_cid, CIDRequest
from app.core.route_ipfs import upload_metadata as ipfs_upload_metadata
from app.utilities.route_verify import compute_cid
from app.utilities.format import format_json, get_ipfs_metadata, get_mongodb_metadata

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

router = APIRouter(prefix="/upload", tags=["upload"])

db_client = MongoDBClient()
load_dotenv()

async def process_metadata(
    asset_id: str,
    wallet_address: str,
    critical_metadata: Dict[str, Any],
    non_critical_metadata: Dict[str, Any],
    file_info: Optional[Dict[str, str]] = None
) -> Dict[str, Any]:
    """
    Core function to process metadata for an asset.
    
    - Checks if asset exists
    - Checks if requesting wallet is the owner of the asset
    - Determines if critical metadata has changed using CID comparison
    - Handles IPFS/blockchain if needed
    - Updates MongoDB with new version or creates new document
    """
    try:
        # Check if asset_id already exists
        existing_doc = None
        try:
            # Query the assets collection directly instead of using get_document_by_id
            existing_doc = db_client.assets_collection.find_one({
                "assetId": asset_id, 
                "isCurrent": True
            })
            
            # Convert ObjectId to string if document exists
            if existing_doc and "_id" in existing_doc:
                existing_doc["_id"] = str(existing_doc["_id"])
        except Exception as e:
            logger.error(f"Error checking for existing document: {str(e)}")
            result = {"asset_id": asset_id, "status": "error", "detail": f"Error checking for existing document: {str(e)}"}
            if file_info:
                result.update(file_info)
            return result
        
        # If document exists, verify wallet ownership
        if existing_doc and existing_doc.get("walletAddress") != wallet_address:
            result = {
                "asset_id": asset_id, 
                "status": "error", 
                "detail": f"Unauthorized: Wallet {wallet_address} is not the owner of this document"
            }
            if file_info:
                result.update(file_info)
            return result
            
        # Extract IPFS-relevant metadata using format.py utility
        ipfs_metadata = get_ipfs_metadata({
            "asset_id": asset_id,
            "wallet_address": wallet_address,
            "critical_metadata": critical_metadata
        })
        
        if existing_doc:
            # Document exists, check if critical metadata changed
            existing_ipfs_hash = existing_doc.get("ipfsHash")
            
            # Compare CIDs directly - compute CID for the current metadata
            new_cid_response = await compute_cid(ipfs_metadata)
            if "computed_cid" not in new_cid_response:
                result = {"asset_id": asset_id, "status": "error", "detail": "Failed to compute CID for metadata."}
                if file_info:
                    result.update(file_info)
                return result
                
            computed_cid = new_cid_response["computed_cid"]
            
            # If CIDs match, then critical metadata has NOT changed
            critical_metadata_changed = computed_cid != existing_ipfs_hash
            
            if critical_metadata_changed:
                # Critical metadata changed - upload to IPFS and blockchain
                # 1) Upload to IPFS using the upload_metadata function directly
                ipfs_data = await ipfs_upload_metadata(ipfs_metadata)
                
                if "result" not in ipfs_data or "cids" not in ipfs_data["result"]:
                    result = {"asset_id": asset_id, "status": "error", "detail": "Failed to obtain CID from IPFS."}
                    if file_info:
                        result.update(file_info)
                    return result
                    
                cid_dict = ipfs_data["result"]["cids"][0]["cid"]
                cid = cid_dict["/"] if isinstance(cid_dict, dict) and "/" in cid_dict else str(cid_dict)
                
                # 2) Store on blockchain
                blockchain_response = await blockchain_store_cid(CIDRequest(cid=str(cid)))
                blockchain_tx_hash = blockchain_response.get("tx_hash")
                if not blockchain_tx_hash:
                    result = {"asset_id": asset_id, "status": "error", "detail": "Failed to store CID on blockchain."}
                    if file_info:
                        result.update(file_info)
                    return result
                
                # 3) Create new version in MongoDB
                try:
                    new_doc_id = db_client.create_new_version(
                        asset_id=asset_id,
                        wallet_address=wallet_address,
                        smart_contract_tx_id=blockchain_tx_hash,
                        ipfs_hash=cid,
                        critical_metadata=critical_metadata,
                        non_critical_metadata=non_critical_metadata
                    )
                except ValueError as e:
                    if "Unauthorized" in str(e):
                        result = {"asset_id": asset_id, "status": "error", "detail": str(e)}
                        if file_info:
                            result.update(file_info)
                        return result
                    raise
                
                # 4) Get version number of new document
                new_doc = db_client.get_document_by_id(asset_id)
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
                # Use the existing IPFS hash and blockchain transaction ID
                existing_tx_hash = existing_doc.get("smartContractTxId")
                
                # Create new version in MongoDB only
                try:
                    new_doc_id = db_client.create_new_version(
                        asset_id=asset_id,
                        wallet_address=wallet_address,
                        smart_contract_tx_id=existing_tx_hash,  # Reuse existing blockchain TX hash
                        ipfs_hash=existing_ipfs_hash,  # Reuse existing IPFS hash
                        critical_metadata=critical_metadata,  # Same as before (or with non-significant differences)
                        non_critical_metadata=non_critical_metadata  # Updated non-critical metadata
                    )
                except ValueError as e:
                    if "Unauthorized" in str(e):
                        result = {"asset_id": asset_id, "status": "error", "detail": str(e)}
                        if file_info:
                            result.update(file_info)
                        return result
                    raise
                
                # Get version number of new document
                new_doc = db_client.assets_collection.find_one({
                    "assetId": asset_id,
                    "isCurrent": True
                })
                version_number = new_doc.get("versionNumber", 0) if new_doc else 0
                
                result = {
                    "asset_id": asset_id,
                    "status": "success",
                    "message": "New version created with only non-critical metadata updates",
                    "document_id": new_doc_id,
                    "version": version_number,
                    "ipfs_cid": existing_ipfs_hash,  # Reusing existing IPFS hash
                    "blockchain_tx_hash": existing_tx_hash,  # Reusing existing blockchain hash
                }
                if file_info:
                    result.update(file_info)
                return result
        else:
            # New document - proceed with normal flow
            # 1) Upload to IPFS using the function directly
            ipfs_data = await ipfs_upload_metadata(ipfs_metadata)
            
            if "result" not in ipfs_data or "cids" not in ipfs_data["result"]:
                result = {"asset_id": asset_id, "status": "error", "detail": "Failed to obtain CID from IPFS."}
                if file_info:
                    result.update(file_info)
                return result
                
            cid_dict = ipfs_data["result"]["cids"][0]["cid"]
            cid = cid_dict["/"] if isinstance(cid_dict, dict) and "/" in cid_dict else str(cid_dict)
            
            # 2) Store on the blockchain
            blockchain_response = await blockchain_store_cid(CIDRequest(cid=str(cid)))
            blockchain_tx_hash = blockchain_response.get("tx_hash")
            if not blockchain_tx_hash:
                result = {"asset_id": asset_id, "status": "error", "detail": "Failed to store CID on blockchain."}
                if file_info:
                    result.update(file_info)
                return result
            
            # 3) Insert into MongoDB
            doc_id = db_client.insert_document(
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
                "version": 1,  # First version
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
@router.post("/metadata")
async def upload_metadata(
    asset_id: str = Form(...),
    wallet_address: str = Form(...),
    critical_metadata: str = Form(...),
    non_critical_metadata: Optional[str] = Form(None)
):
    """
    Upload metadata directly (not as a file).
    
    - Takes asset_id, wallet_address, and metadata as form fields
    - Checks if critical metadata has changed using CID comparison
    - Stores in IPFS only if changed
    - Registers on blockchain only if changed
    - Updates MongoDB
    """
    try:
        # Parse JSON strings
        critical_md = json.loads(critical_metadata)
        non_critical_md = json.loads(non_critical_metadata) if non_critical_metadata else {}
        
        # Process metadata
        return await process_metadata(
            asset_id=asset_id,
            wallet_address=wallet_address,
            critical_metadata=critical_md,
            non_critical_metadata=non_critical_md
        )
            
    except Exception as e:
        logger.error(f"Error processing metadata: {str(e)}")
        return {"asset_id": asset_id, "status": "error", "detail": f"Error processing metadata: {str(e)}"}

@router.post("/json")
async def upload_json(
    files: List[UploadFile] = File(...),
    wallet_address: str = Form(...)
):
    """
    Process JSON files uploaded by the user.
    
    - Each JSON file must have: asset_id, critical_metadata, optional non_critical_metadata
    - Each file represents a single document/asset
    - Duplicate asset_ids are skipped (first occurrence is used)
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
            non_critical_metadata = data.get("non_critical_metadata") or {}
            
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
            result = await process_metadata(
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

@router.post("/csv")
async def upload_csv(
    files: List[UploadFile] = File(...),
    wallet_address: str = Form(...),
    critical_metadata_fields: List[str] = Query(
        ..., 
        description="List of CSV columns that represent 'critical' metadata."
    )
):
    """
    Process CSV files uploaded by the user.
    
    - Each row in the CSV is treated as a distinct record with a unique asset_id
    - Must supply 'critical_metadata_fields' to identify which columns are critical
    - Each row must have an 'asset_id' column
    - Duplicate asset_ids are skipped (first occurrence is used)
    """
    seen_asset_ids = set()
    results = []
    
    # Helper to parse CSV rows into document dictionaries
    def parse_csv(file_content: bytes, critical_fields: List[str]) -> List[Dict[str, Any]]:
        """
        Reads CSV bytes, returns a list of dicts each with:
            asset_id, critical_metadata, non_critical_metadata.
        Expects 'asset_id' column to exist.
        """
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
                result = await process_metadata(
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
