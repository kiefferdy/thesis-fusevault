import httpx
import logging
import os
from typing import Dict, Any
from dotenv import load_dotenv
from app.utilities.format import format_json, get_ipfs_metadata

logger = logging.getLogger(__name__)

class IPFSService:
    def __init__(self):
        load_dotenv()
        self.storage_service_url = os.getenv("WEB3_STORAGE_SERVICE_URL")

    async def store_metadata(self, metadata: Dict[str, Any]) -> str:
        try:
            formatted_metadata = format_json(get_ipfs_metadata(metadata))

            files = {"files": ("metadata.json", formatted_metadata, "application/json")}

            async with httpx.AsyncClient(timeout=90.0) as client:
                response = await client.post(f"{self.storage_service_url}/upload", files=files)
                response.raise_for_status()

            cid_dict = response.json()["result"]["cids"][0]["cid"]
            cid = cid_dict["/"] if isinstance(cid_dict, dict) and "/" in cid_dict else str(cid_dict)

            logger.info(f"Successfully stored metadata on IPFS. CID: {cid}")
            return cid

        except httpx.HTTPError as exc:
            logger.error(f"HTTP error uploading to IPFS: {str(exc)}")
            raise
        except Exception as e:
            logger.error(f"General error uploading metadata to IPFS: {str(e)}")
            raise

    async def retrieve_metadata(self, cid: str) -> Dict[str, Any]:
        try:
            async with httpx.AsyncClient(timeout=90.0) as client:
                response = await client.get(f"{self.storage_service_url}/file/{cid}/contents")
                response.raise_for_status()

            metadata = response.json()
            logger.info(f"Successfully retrieved metadata from IPFS with CID: {cid}")
            return metadata

        except httpx.HTTPError as exc:
            logger.error(f"HTTP error retrieving from IPFS: {str(exc)}")
            raise
        except Exception as e:
            logger.error(f"General error retrieving metadata from IPFS: {str(e)}")
            raise
