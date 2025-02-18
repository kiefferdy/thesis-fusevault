from fastapi import APIRouter, HTTPException, UploadFile, File, Form, Query
import pandas as pd
import json
import logging
import os
from io import BytesIO, StringIO
from dotenv import load_dotenv
from typing import List, Dict, Any

from app.core.mongodb_client import MongoDBClient
from app.core.route_ipfs import upload_files as ipfs_upload_files
from app.core.route_sc import store_cid as blockchain_store_cid, CIDRequest

# Initialize logger
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Create unified router with prefix /storage
router = APIRouter(prefix="/storage", tags=["storage"])

# Initialize MongoDB client and load environment variables
db_client = MongoDBClient()
load_dotenv()


@router.post("/store")
async def store_data(
    file: UploadFile = File(...),
    user_wallet_address: str = Form(...),
    file_type: str = Form(..., description="Specify file type: 'json' or 'csv'"),
    critical_metadata_fields: List[str] = Query(..., description="Comma-separated list of critical metadata fields"),
):
    """
    Handles both JSON and CSV file uploads:
      - If JSON, extracts critical and non-critical metadata, then uploads it to IPFS & Blockchain.
      - If CSV, prompts user to specify critical metadata fields, validates them, and converts to JSON before proceeding.
    """

    # Read the file content
    try:
        file_content = await file.read()
    except Exception as e:
        logger.error(f"Error reading file: {e}")
        raise HTTPException(status_code=400, detail="Error reading uploaded file.")

    if file_type.lower() == "json":
        # Handle JSON file upload
        try:
            json_data = json.loads(file_content.decode("utf-8"))
        except Exception as e:
            logger.error(f"Error parsing JSON file: {e}")
            raise HTTPException(status_code=400, detail="Invalid JSON file.")

        # Extract required fields
        asset_id = json_data.get("asset_id")
        critical_metadata = json_data.get("critical_metadata")
        non_critical_metadata = json_data.get("non_critical_metadata")

        if not asset_id or not critical_metadata or not non_critical_metadata:
            raise HTTPException(
                status_code=400,
                detail="Missing required fields in JSON: asset_id, critical_metadata, or non_critical_metadata."
            )

    elif file_type.lower() == "csv":
        # Handle CSV file upload
        try:
            csv_data = pd.read_csv(StringIO(file_content.decode("utf-8")))
        except Exception as e:
            logger.error(f"Error parsing CSV file: {e}")
            raise HTTPException(status_code=400, detail="Invalid CSV file.")

        # Validate that user-specified critical metadata fields exist in the CSV
        missing_fields = [field for field in critical_metadata_fields if field not in csv_data.columns]
        if missing_fields:
            raise HTTPException(
                status_code=400,
                detail=f"The following critical metadata fields are missing from the CSV: {missing_fields}"
            )

        # Convert CSV rows into JSON format
        json_records = csv_data.to_dict(orient="records")

        # Create a structured JSON payload
        asset_id = "AUTO-GENERATED-ID"  # Can be dynamically generated or provided by the user
        critical_metadata = {field: json_records[0][field] for field in critical_metadata_fields}
        non_critical_metadata = {
            key: value for key, value in json_records[0].items() if key not in critical_metadata_fields
        }

    else:
        raise HTTPException(status_code=400, detail="Invalid file type. Use 'json' or 'csv'.")

    # Construct JSON payload for IPFS
    ipfs_payload = {
        "asset_id": asset_id,
        "user_wallet_address": user_wallet_address,
        "critical_metadata": critical_metadata,
        "non_critical_metadata": non_critical_metadata,
    }

    # Convert to JSON and prepare for IPFS upload
    ipfs_file_content = json.dumps(ipfs_payload).encode("utf-8")
    ipfs_upload_file = UploadFile(
        filename="ipfs_payload.json",
        file=BytesIO(ipfs_file_content)
    )

    # Upload JSON to IPFS
    try:
        ipfs_data = await ipfs_upload_files(files=[ipfs_upload_file])
        if "cids" not in ipfs_data or not ipfs_data["cids"]:
            raise HTTPException(status_code=500, detail="Failed to obtain CID from IPFS.")
        cid_dict = ipfs_data["cids"][0]["cid"]
        cid = cid_dict["/"] if isinstance(cid_dict, dict) and "/" in cid_dict else str(cid_dict)
        logger.info(f"IPFS upload successful, CID: {cid}")
    except Exception as e:
        logger.error(f"IPFS upload error: {e}")
        raise HTTPException(status_code=500, detail=f"IPFS upload error: {str(e)}")

    # Store CID on the blockchain
    try:
        blockchain_response = await blockchain_store_cid(CIDRequest(cid=str(cid)))
        blockchain_tx_hash = blockchain_response.get("tx_hash")
        if not blockchain_tx_hash:
            raise HTTPException(status_code=500, detail="Failed to store CID on blockchain.")
        logger.info(f"Blockchain storage successful, tx hash: {blockchain_tx_hash}")
    except Exception as e:
        logger.error(f"Blockchain error: {e}")
        raise HTTPException(status_code=500, detail=f"Blockchain error: {str(e)}")

    # Insert document into MongoDB
    try:
        doc_id = db_client.insert_document(
            asset_id=asset_id,
            user_wallet_address=user_wallet_address,
            smart_contract_tx_id=blockchain_tx_hash,
            ipfs_hash=cid,
            critical_metadata=critical_metadata,
            non_critical_metadata=non_critical_metadata
        )
        logger.info(f"Document inserted into MongoDB with id: {doc_id}")
    except Exception as e:
        logger.error(f"Database error: {e}")
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")

    return {
        "status": "success",
        "document_id": doc_id,
        "ipfs_cid": cid,
        "blockchain_tx_hash": blockchain_tx_hash,
    }