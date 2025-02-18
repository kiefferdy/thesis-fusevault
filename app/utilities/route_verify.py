from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
import json
import httpx

router = APIRouter(prefix="/verify", tags=["verify"])

class MetadataPayload(BaseModel):
    asset_id: str
    user_wallet_address: str
    critical_metadata: dict

    class Config:
        extra = "allow"

@router.post("/calculate-cid")
async def calculate_cid(metadata: MetadataPayload):
    """
    Accepts a JSON payload containing metadata. Only the asset_id, user_wallet_address, 
    and critical_metadata fields are used. The filtered payload is converted to a JSON file 
    and forwarded to the Node.js /calculate-cid endpoint.
    """
    try:
        # Filter out only the fields that go on IPFS
        ipfs_payload = {
            "asset_id": metadata.asset_id,
            "user_wallet_address": metadata.user_wallet_address,
            "critical_metadata": metadata.critical_metadata
        }

        # Serialize JSON with minimal separators (no extra spaces, no newlines).
        ipfs_json_bytes = json.dumps(
            ipfs_payload,
            separators=(",", ":")
        ).encode("utf-8")

        # Prepare the file upload for Node
        files = {
            "file": (
                "ipfs_payload.json", 
                ipfs_json_bytes, 
                "application/json"
            )
        }

        # Post to the Node.js /calculate-cid
        async with httpx.AsyncClient() as client:
            response = await client.post(
                "http://localhost:8080/calculate-cid",
                files=files
            )
        response.raise_for_status()
        return response.json()

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
