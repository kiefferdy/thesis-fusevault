from fastapi import APIRouter, HTTPException
import httpx
import os
import logging
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Set up logging
logging.basicConfig(level=logging.INFO)

router = APIRouter(prefix="/conn", tags=["ipfs-smartcontract"])

# Get service URLs from environment variables
WEB3_STORAGE_SERVICE_URL = os.getenv("WEB3_STORAGE_SERVICE_URL", "http://localhost:8080")
SMART_CONTRACT_SERVICE_URL = os.getenv("SMART_CONTRACT_SERVICE_URL", "http://localhost:8000")

@router.post("/extract_and_store/{cid}")
async def extract_and_store(cid: str):
    """
    Extracts the CID from IPFS and stores it in the blockchain via the smart contract.
    """
    try:
        async with httpx.AsyncClient(timeout=60.0) as client:
            # Fetch CID from IPFS
            ipfs_url = f"{WEB3_STORAGE_SERVICE_URL}/file/{cid}"
            logging.info(f"Fetching CID from IPFS: {ipfs_url}")

            ipfs_response = await client.get(ipfs_url)
            ipfs_response.raise_for_status()
            ipfs_data = ipfs_response.json()
            
            logging.info(f"IPFS Response Data: {ipfs_data}")

            # Validate IPFS response
            if not ipfs_data or "url" not in ipfs_data:
                raise HTTPException(status_code=400, detail="Invalid CID received from IPFS")

            # Send CID to smart contract
            payload = {"cid": cid}
            headers = {"Content-Type": "application/json"}

            sc_url = f"{SMART_CONTRACT_SERVICE_URL}/store_cid/"
            logging.info(f"Sending CID to Smart Contract: {sc_url} with payload {payload}")

            sc_response = await client.post(sc_url, json=payload, headers=headers)
            sc_response.raise_for_status()
            sc_data = sc_response.json()

            logging.info(f"Smart Contract Response: {sc_data}")

            return {
                "cid": cid,
                "blockchain_tx": sc_data.get("blockchain_tx"),
            }

    except httpx.HTTPStatusError as exc:
        logging.error(f"HTTP Error: {exc.response.status_code} - {exc.response.text}")
        raise HTTPException(
            status_code=exc.response.status_code,
            detail=f"Service Error: {exc.response.text}",
        )

    except httpx.RequestError as exc:
        logging.error(f"Request Error: {str(exc)}")
        raise HTTPException(
            status_code=500,
            detail="Failed to connect to external service.",
        )

    except Exception as exc:
        logging.error(f"Unexpected Error: {str(exc)}")
        raise HTTPException(
            status_code=500,
            detail=f"Unexpected Error: {str(exc)}",
        )