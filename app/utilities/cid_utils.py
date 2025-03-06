from typing import Any, Dict
import httpx
from fastapi import HTTPException
from app.utilities.format import format_json, get_ipfs_metadata
import logging
import os
from dotenv import load_dotenv

load_dotenv()

WEB3_STORAGE_SERVICE_URL = os.getenv("WEB3_STORAGE_SERVICE_URL")

async def compute_cid(metadata: dict) -> str:
    """
    Compute CID from given metadata by interacting with IPFS Node service.
    """
    formatted_metadata = format_json(metadata)
    files = {
        "file": ("metadata.json", formatted_metadata, "application/json")
    }

    try:
        async with httpx.AsyncClient(timeout=90.0) as client:
            response = await client.post(
                f"{os.getenv('WEB3_STORAGE_SERVICE_URL')}/calculate-cid",
                files=files
            )
            response.raise_for_status()

        result = response.json()
        computed_cid = result.get("computed_cid")
        if not computed_cid:
            raise ValueError("No CID returned from IPFS service")

        return computed_cid

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

async def verify_cid(metadata: Dict[str, Any], provided_cid: str) -> bool:
    """
    Compares provided CID against computed CID from metadata.
    """
    computed_cid = await compute_cid(get_ipfs_metadata(metadata))
    return computed_cid == provided_cid
