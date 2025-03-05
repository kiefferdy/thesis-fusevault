from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
import httpx
from app.utilities.format import get_ipfs_metadata, format_json

router = APIRouter(prefix="/verify", tags=["verify"])

class MetadataPayload(BaseModel):
    asset_id: str
    wallet_address: str
    critical_metadata: dict

    class Config:
        extra = "allow"

class CIDCheckPayload(BaseModel):
    cid: str
    metadata: dict

@router.post("/compute-cid")
async def compute_cid(metadata: dict):
    """
    Accepts a JSON payload containing metadata and forwards it as-is to the 
    Node.js /calculate-cid endpoint.
    """
    try:
        # Format the metadata using the consistent format_json utility
        ipfs_json_bytes = format_json(metadata)

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

@router.post("/check-cid")
async def check_cid(payload: CIDCheckPayload):
    """
    Verifies if a given CID matches the CID that would be generated from the provided metadata.
    
    Steps:
    1. Extract IPFS-relevant metadata using get_ipfs_metadata
    2. Compute the CID for the extracted metadata using /compute-cid
    3. Compare the computed CID with the provided CID
    
    Args:
        payload: Contains a CID to verify and metadata to check against
        
    Returns:
        dict: Contains a boolean 'verified' field indicating if the CIDs match
    """
    try:
        # Extract only the IPFS-relevant fields from the metadata
        ipfs_metadata = get_ipfs_metadata(payload.metadata)
        
        # Calculate the CID based on the filtered metadata
        calc_result = await compute_cid(ipfs_metadata)
        computed_cid = calc_result.get("computed_cid")
        
        if not computed_cid:
            raise HTTPException(status_code=500, detail="Failed to compute CID from metadata")
        
        # Compare the CIDs
        verified = computed_cid == payload.cid
        
        return {
            "verified": verified,
            "provided_cid": payload.cid,
            "computed_cid": computed_cid
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
