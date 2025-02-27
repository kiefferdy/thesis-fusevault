from fastapi import APIRouter, HTTPException, UploadFile, File, Form, Query
from typing import List, Dict, Any, Optional
from io import BytesIO, StringIO
import pandas as pd
import json
import logging
import os
from dotenv import load_dotenv

from app.core.mongodb_client import MongoDBClient
from app.core.route_ipfs import upload_files as ipfs_upload_files
from app.core.route_sc import store_cid as blockchain_store_cid, CIDRequest

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

router = APIRouter(prefix="/storage", tags=["storage"])

db_client = MongoDBClient()
load_dotenv()

@router.post("/store")
async def store_data(
    files: List[UploadFile] = File(...),
    wallet_address: str = Form(...),
    critical_metadata_fields: Optional[List[str]] = Query(
        None, 
        description="List of CSV columns that represent 'critical' metadata (only used if uploading a CSV)."
    )
):
    """
    Accepts multiple uploaded files (JSON or CSV).
    
    - For each JSON file:
       * Must have: asset_id, critical_metadata, optional non_critical_metadata.
    - For each CSV file:
       * Must supply 'critical_metadata_fields' to know which columns are critical.
       * Each row is treated as a distinct record with a unique asset_id.
         The first row found for an asset_id is used; duplicates for that ID are discarded.
         
    All records are individually:
      - Uploaded to IPFS (only asset_id, wallet_address, critical_metadata).
      - Stored on-chain (CID).
      - Inserted into MongoDB (full metadata).
      
    Duplicate asset IDs across all files are discarded (we only take the first occurrence).
    """
    # A memory of all asset_ids we've handled to skip duplicates
    seen_asset_ids = set()

    # We'll accumulate the results
    results = []

    # Helper function to store a single record (doc)
    async def store_single_document(
        asset_id: str,
        wallet_addr: str,
        critical_md: Dict[str, Any],
        non_critical_md: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Takes a single doc's data, uploads it to IPFS,
        stores the CID on the blockchain, and inserts into MongoDB.
        Returns a dict with success info or error.
        """
        # Check if this asset_id already exists
        existing_doc = None
        try:
            existing_doc = db_client.get_document_by_id(asset_id)
        except ValueError:
            # Document doesn't exist which is fine for new documents
            pass
        except Exception as e:
            return {"asset_id": asset_id, "status": "error", "detail": f"Error checking for existing document: {str(e)}"}
        
        if existing_doc:
            # If document already exists, create a new version
            try:
                # 1) Minimal IPFS payload for new version
                ipfs_payload = {
                    "asset_id": asset_id,
                    "wallet_address": wallet_addr,
                    "critical_metadata": critical_md,
                }

                # 2) Upload to IPFS
                ipfs_file_content = json.dumps(ipfs_payload).encode("utf-8")
                ipfs_upload_file = UploadFile(
                    filename=f"ipfs_payload_{asset_id}.json",
                    file=BytesIO(ipfs_file_content)
                )
                ipfs_data = await ipfs_upload_files(files=[ipfs_upload_file])
                if "cids" not in ipfs_data or not ipfs_data["cids"]:
                    return {"asset_id": asset_id, "status": "error", "detail": "Failed to obtain CID from IPFS."}
                cid_dict = ipfs_data["cids"][0]["cid"]
                cid = cid_dict["/"] if isinstance(cid_dict, dict) and "/" in cid_dict else str(cid_dict)

                # 3) Store on the blockchain
                blockchain_response = await blockchain_store_cid(CIDRequest(cid=str(cid)))
                blockchain_tx_hash = blockchain_response.get("tx_hash")
                if not blockchain_tx_hash:
                    return {"asset_id": asset_id, "status": "error", "detail": "Failed to store CID on blockchain."}

                # 4) Create new version in MongoDB
                new_doc_id = db_client.create_new_version(
                    asset_id=asset_id,
                    wallet_address=wallet_addr,
                    smart_contract_tx_id=blockchain_tx_hash,
                    ipfs_hash=cid,
                    critical_metadata=critical_md,
                    non_critical_metadata=non_critical_md
                )
                
                # Get version number of new document
                new_doc = db_client.get_document_by_id(asset_id)
                version_number = new_doc.get("versionNumber", 0)
                
                return {
                    "asset_id": asset_id,
                    "status": "success",
                    "message": "New version created",
                    "document_id": new_doc_id,
                    "version": version_number,
                    "ipfs_cid": cid,
                    "blockchain_tx_hash": blockchain_tx_hash,
                }
            except Exception as e:
                return {"asset_id": asset_id, "status": "error", "detail": f"Error creating new version: {str(e)}"}
        else:
            # New document - proceed with normal flow
            try:
                # 1) Minimal IPFS payload
                ipfs_payload = {
                    "asset_id": asset_id,
                    "wallet_address": wallet_addr,
                    "critical_metadata": critical_md,
                }

                # 2) Upload to IPFS
                ipfs_file_content = json.dumps(ipfs_payload).encode("utf-8")
                ipfs_upload_file = UploadFile(
                    filename=f"ipfs_payload_{asset_id}.json",
                    file=BytesIO(ipfs_file_content)
                )
                ipfs_data = await ipfs_upload_files(files=[ipfs_upload_file])
                if "cids" not in ipfs_data or not ipfs_data["cids"]:
                    return {"asset_id": asset_id, "status": "error", "detail": "Failed to obtain CID from IPFS."}
                cid_dict = ipfs_data["cids"][0]["cid"]
                cid = cid_dict["/"] if isinstance(cid_dict, dict) and "/" in cid_dict else str(cid_dict)

                # 3) Store on the blockchain
                blockchain_response = await blockchain_store_cid(CIDRequest(cid=str(cid)))
                blockchain_tx_hash = blockchain_response.get("tx_hash")
                if not blockchain_tx_hash:
                    return {"asset_id": asset_id, "status": "error", "detail": "Failed to store CID on blockchain."}

                # 4) Insert into MongoDB
                doc_id = db_client.insert_document(
                    asset_id=asset_id,
                    wallet_address=wallet_addr,
                    smart_contract_tx_id=blockchain_tx_hash,
                    ipfs_hash=cid,
                    critical_metadata=critical_md,
                    non_critical_metadata=non_critical_md
                )
                return {
                    "asset_id": asset_id,
                    "status": "success",
                    "message": "Document created",
                    "document_id": doc_id,
                    "version": 1,  # First version
                    "ipfs_cid": cid,
                    "blockchain_tx_hash": blockchain_tx_hash,
                }
            except Exception as e:
                return {"asset_id": asset_id, "status": "error", "detail": f"Database error: {str(e)}"}

    # Helper to parse CSV rows into doc dicts
    def parse_csv(file_content: bytes, critical_fields: List[str]) -> List[Dict[str, Any]]:
        """
        Reads CSV bytes, returns a list of dicts each with:
            asset_id, critical_metadata, non_critical_metadata.
        Expects 'asset_id' column to exist or otherwise you might generate one.
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

    # Process each uploaded file
    for file_obj in files:
        filename_lower = file_obj.filename.lower()
        try:
            content = await file_obj.read()
        except Exception as e:
            # If we can't even read the file, skip it
            logger.error(f"Could not read file {file_obj.filename}: {str(e)}")
            results.append({
                "filename": file_obj.filename,
                "status": "error",
                "detail": f"Could not read file: {str(e)}"
            })
            continue

        # Decide how to parse this file (JSON or CSV)
        if filename_lower.endswith(".json"):
            # Parse JSON
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

            # Now store it - this will handle both new documents and new versions
            store_result = await store_single_document(
                asset_id, wallet_address, critical_metadata, non_critical_metadata
            )
            # Attach filename to the store result for clarity
            store_result["filename"] = file_obj.filename
            results.append(store_result)

        elif filename_lower.endswith(".csv"):
            # Parse CSV
            if not critical_metadata_fields:
                results.append({
                    "filename": file_obj.filename,
                    "status": "error",
                    "detail": "No 'critical_metadata_fields' provided for CSV."
                })
                continue
            try:
                row_docs = parse_csv(content, critical_metadata_fields)
            except Exception as e:
                results.append({
                    "filename": file_obj.filename,
                    "status": "error",
                    "detail": f"CSV parse error: {str(e)}"
                })
                continue

            # For each row, store if not duplicate
            for row_doc in row_docs:
                asset_id = row_doc["asset_id"]
                # Check duplicates
                if asset_id in seen_asset_ids:
                    results.append({
                        "asset_id": asset_id,
                        "filename": file_obj.filename,
                        "status": "skipped",
                        "detail": "Duplicate asset_id found in CSV; ignoring this row."
                    })
                    continue

                seen_asset_ids.add(asset_id)

                # This will handle both new documents and new versions
                store_result = await store_single_document(
                    asset_id,
                    wallet_address,
                    row_doc["critical_metadata"],
                    row_doc["non_critical_metadata"]
                )
                # Attach file name for clarity
                store_result["filename"] = file_obj.filename
                results.append(store_result)
        else:
            # Unrecognized file extension
            results.append({
                "filename": file_obj.filename,
                "status": "error",
                "detail": "Unsupported file type. Use .json or .csv."
            })

    return {
        "upload_count": len(results),
        "results": results
    }