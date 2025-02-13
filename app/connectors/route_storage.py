from fastapi import APIRouter, HTTPException, UploadFile, File, Form
from typing import Dict, Any
import json
import logging
import os
from io import BytesIO
from dotenv import load_dotenv

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
    user_wallet_address: str = Form(...)
):
    """
    Combined endpoint that:
      1. Receives a JSON file upload containing asset_id, critical_metadata, and non_critical_metadata.
      2. Accepts user_wallet_address as a separate form parameter.
      3. Constructs a new JSON payload for IPFS that includes only asset_id, user_wallet_address, and critical_metadata.
      4. Uploads the new payload to IPFS.
      5. Stores the resulting IPFS CID on the blockchain.
      6. Inserts a document into MongoDB with both critical and non-critical metadata.
    """
    # Read and parse the uploaded JSON file
    try:
        file_content = await file.read()
        json_data = json.loads(file_content.decode("utf-8"))
    except Exception as e:
        logger.error(f"Error reading/parsing JSON file: {e}")
        raise HTTPException(status_code=400, detail="Invalid JSON file.")

    # Extract required fields from the JSON file
    asset_id = json_data.get("asset_id")
    critical_metadata = json_data.get("critical_metadata")
    non_critical_metadata = json_data.get("non_critical_metadata")

    if not asset_id or not critical_metadata or not non_critical_metadata:
        raise HTTPException(
            status_code=400,
            detail="Missing required fields in JSON file: asset_id, critical_metadata, or non_critical_metadata."
        )

    # Construct a new JSON payload for IPFS containing only the critical data
    ipfs_payload = {
        "asset_id": asset_id,
        "user_wallet_address": user_wallet_address,
        "critical_metadata": critical_metadata
    }
    ipfs_file_content = json.dumps(ipfs_payload).encode("utf-8")
    # Create an in-memory UploadFile without the content_type argument
    ipfs_upload_file = UploadFile(
        filename="ipfs_payload.json",
        file=BytesIO(ipfs_file_content)
    )

    # Directly call the IPFS function with the new file
    try:
        ipfs_data = await ipfs_upload_files(files=[ipfs_upload_file])
        if "cids" not in ipfs_data or not ipfs_data["cids"]:
            raise HTTPException(status_code=500, detail="Failed to obtain CID from IPFS.")
        # Extract the CID value
        cid_value = ipfs_data["cids"][0]["cid"]
        if isinstance(cid_value, dict):
            cid = cid_value.get("/")
        else:
            cid = cid_value
        logger.info(f"IPFS upload successful, CID: {cid}")
    except Exception as e:
        logger.error(f"IPFS upload error: {e}")
        raise HTTPException(status_code=500, detail=f"IPFS upload error: {str(e)}")

    # Directly call the blockchain function
    try:
        blockchain_response = await blockchain_store_cid(CIDRequest(cid=cid))
        blockchain_tx_hash = blockchain_response.get("tx_hash")
        if not blockchain_tx_hash:
            raise HTTPException(status_code=500, detail="Failed to store CID on blockchain.")
        logger.info(f"Blockchain storage successful, tx hash: {blockchain_tx_hash}")
    except Exception as e:
        logger.error(f"Blockchain error: {e}")
        raise HTTPException(status_code=500, detail=f"Blockchain error: {str(e)}")

    # Insert document into MongoDB with both critical and non-critical metadata
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
