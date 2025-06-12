import httpx
import json
import logging
from typing import Dict, Any, List
from fastapi import UploadFile, HTTPException
from app.utilities.format import format_json, get_ipfs_metadata
from app.config import settings

logger = logging.getLogger(__name__)

class IPFSService:
    def __init__(self):
        self.storage_service_url = settings.web3_storage_service_url
        logger.info(f"Using Web3 Storage service at: {self.storage_service_url}")
        
    async def test_connection(self) -> Dict[str, Any]:
        """Test connection to web3 storage service for debugging."""
        try:
            # Configure httpx for IPv6 support on Railway
            limits = httpx.Limits(max_keepalive_connections=5, max_connections=10)
            async with httpx.AsyncClient(timeout=30.0, limits=limits) as client:
                response = await client.get(f"{self.storage_service_url}/health")
                response.raise_for_status()
                result = response.json()
                logger.info(f"Web3 storage service health check successful: {result}")
                return {"status": "connected", "health_data": result}
        except Exception as exc:
            logger.error(f"Web3 storage service health check failed: {exc}")
            logger.error(f"Service URL: {self.storage_service_url}")
            return {"status": "failed", "error": str(exc), "url": self.storage_service_url}

    async def store_metadata(self, metadata: Dict[str, Any]) -> str:
        """
        Store metadata on IPFS.
        
        Args:
            metadata: Metadata to store on IPFS
            
        Returns:
            String CID of the stored metadata
        """
        try:
            formatted_metadata = format_json(get_ipfs_metadata(metadata))

            files = {"files": ("metadata.json", formatted_metadata, "application/json")}

            async with httpx.AsyncClient(timeout=90.0) as client:
                response = await client.post(f"{self.storage_service_url}/upload", files=files)
                response.raise_for_status()

            # Get the response JSON and log it for debugging
            response_json = response.json()
            logger.debug(f"IPFS service response: {response_json}")

            # Extract CID from the response
            if "cids" in response_json and len(response_json["cids"]) > 0 and "cid" in response_json["cids"][0]:
                cid_dict = response_json["cids"][0]["cid"]
                if isinstance(cid_dict, dict) and "/" in cid_dict:
                    cid = cid_dict["/"]
                else:
                    cid = str(cid_dict)
            else:
                raise ValueError(f"Unable to extract CID from response: {response_json}")
            
            if not cid:
                raise ValueError(f"Unable to extract CID from response: {response_json}")

            logger.info(f"Successfully stored metadata on IPFS. CID: {cid}")
            return cid

        except httpx.ConnectError as exc:
            logger.error(f"Connection error to Web3 storage service: {exc}")
            logger.error(f"Attempted URL: {self.storage_service_url}/upload")
            raise HTTPException(status_code=503, detail=f"Cannot connect to Web3 storage service at {self.storage_service_url}")
        except httpx.HTTPError as exc:
            logger.error(f"HTTP error uploading to IPFS: {str(exc)}")
            logger.error(f"Response status: {getattr(exc.response, 'status_code', 'unknown')}")
            logger.error(f"Response body: {getattr(exc.response, 'text', 'unknown')}")
            raise
        except Exception as e:
            logger.error(f"General error uploading metadata to IPFS: {str(e)}")
            raise

    async def retrieve_metadata(self, cid: str) -> Dict[str, Any]:
        """
        Retrieve metadata from IPFS by CID.
        
        Args:
            cid: Content identifier to retrieve
            
        Returns:
            Dict containing the metadata
        """
        try:
            async with httpx.AsyncClient(timeout=90.0) as client:
                try:
                    # Try using the storage service URL first
                    response = await client.get(f"{self.storage_service_url}/file/{cid}/contents")
                    response.raise_for_status()
                except httpx.HTTPStatusError as exc:
                    # If the storage service fails, try using the specified IPFS gateways
                    # Primary gateway: w3s.link
                    try:
                        w3s_url = f"https://{cid}.ipfs.w3s.link"
                        logger.info(f"Storage service failed, trying W3S gateway: {w3s_url}")
                        response = await client.get(w3s_url)
                        response.raise_for_status()
                    except Exception as w3s_error:
                        # Fallback gateway: dweb.link
                        logger.info(f"W3S gateway failed: {str(w3s_error)}, trying dweb.link")
                        dweb_url = f"https://{cid}.ipfs.dweb.link"
                        try:
                            response = await client.get(dweb_url)
                            response.raise_for_status()
                        except Exception as dweb_error:
                            # If both gateways fail, re-raise the original exception
                            logger.error(f"All IPFS gateways failed. Storage service error: {exc}, W3S error: {w3s_error}, Dweb error: {dweb_error}")
                            raise exc
                
                # Try to parse as JSON
                try:
                    metadata = response.json()
                except json.JSONDecodeError:
                    # If it's not valid JSON, try to handle it as text
                    text_content = response.text
                    try:
                        metadata = json.loads(text_content)
                    except json.JSONDecodeError:
                        # If we still can't parse it, return a minimal fallback
                        logger.warning(f"Retrieved content is not valid JSON: {text_content[:100]}...")
                        metadata = {
                            "critical_metadata": {"recovered_content": text_content[:500]},
                            "retrieval_error": "Content is not valid JSON"
                        }
                
                logger.info(f"Successfully retrieved metadata from IPFS with CID: {cid}")
                return metadata

        except httpx.HTTPError as exc:
            logger.error(f"HTTP error retrieving from IPFS: {str(exc)}")
            raise
        except Exception as e:
            logger.error(f"General error retrieving metadata from IPFS: {str(e)}")
            raise
            
    async def upload_files(self, files: List[UploadFile]) -> Dict[str, Any]:
        """
        Upload multiple files to IPFS.
        
        Args:
            files: List of files to upload
            
        Returns:
            Dict containing result information including CIDs
        """
        try:
            # Prepare multipart form data for multiple files
            multipart_data = []
            for file in files:
                file_content = await file.read()
                multipart_data.append(
                    ("files", (file.filename, file_content, file.content_type))
                )
            
            async with httpx.AsyncClient(timeout=90.0) as client:
                response = await client.post(
                    f"{self.storage_service_url}/upload",
                    files=multipart_data
                )
                response.raise_for_status()

            result = response.json()
            logger.info(f"Successfully uploaded {len(files)} files to IPFS")
            return result
            
        except httpx.HTTPError as exc:
            logger.error(f"HTTP error uploading files to IPFS: {str(exc)}")
            raise
        except Exception as e:
            logger.error(f"General error uploading files to IPFS: {str(e)}")
            raise
            
    async def get_file_url(self, cid: str) -> Dict[str, Any]:
        """
        Get the URL for a file stored on IPFS.
        
        Args:
            cid: Content identifier of the file
            
        Returns:
            Dict containing the URL information
        """
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(f"{self.storage_service_url}/file/{cid}")
                response.raise_for_status()
                
            result = response.json()
            return result
            
        except httpx.HTTPError as exc:
            logger.error(f"HTTP error getting file URL: {str(exc)}")
            raise
        except Exception as e:
            logger.error(f"General error getting file URL: {str(e)}")
            raise
            
    async def get_file_contents(self, cid: str, response_type: str = "text") -> Any:
        """
        Get the contents of a file stored on IPFS.
        
        Args:
            cid: Content identifier of the file
            response_type: Type of response to return ('text', 'json', or 'bytes')
            
        Returns:
            The file contents in the specified format
        """
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(f"{self.storage_service_url}/file/{cid}/contents")
                response.raise_for_status()
                
            if response_type == "json":
                return response.json()
            elif response_type == "bytes":
                return response.content
            else:
                return response.text
                
        except httpx.HTTPError as exc:
            logger.error(f"HTTP error getting file contents: {str(exc)}")
            raise
        except Exception as e:
            logger.error(f"General error getting file contents: {str(e)}")
            raise
    
    async def compute_cid(self, metadata: Dict[str, Any]) -> str:
        """
        Compute CID from given metadata by interacting with IPFS Node service.
        
        Args:
            metadata: Metadata to compute CID for
            
        Returns:
            Computed CID string
        
        Raises:
            HTTPException: If there's an error computing the CID
        """
        try:
            # Format the metadata using the consistent format_json utility
            formatted_metadata = format_json(metadata)
            
            # Create a file content for direct multipart upload
            files = {
                "file": ("metadata.json", formatted_metadata, "application/json")
            }

            async with httpx.AsyncClient(timeout=90.0) as client:
                response = await client.post(
                    f"{self.storage_service_url}/calculate-cid",
                    files=files
                )
                response.raise_for_status()

            result = response.json()
            computed_cid = result.get("computed_cid")
            
            if not computed_cid:
                raise ValueError("No CID returned from IPFS service")
                
            return computed_cid

        except Exception as e:
            logger.error(f"Error computing CID: {str(e)}")
            raise HTTPException(status_code=500, detail=str(e))

    async def verify_cid(self, metadata: Dict[str, Any], provided_cid: str) -> bool:
        """
        Compares provided CID against computed CID from metadata.
        
        Args:
            metadata: Metadata to verify
            provided_cid: CID to compare against
            
        Returns:
            Boolean indicating whether CIDs match
            
        Raises:
            HTTPException: If there's an error verifying the CID
        """
        try:
            # Extract only the IPFS-relevant fields from the metadata if needed
            ipfs_metadata = get_ipfs_metadata(metadata)
            
            # Calculate the CID based on the filtered metadata
            computed_cid = await self.compute_cid(ipfs_metadata)
            
            # Compare the CIDs
            return computed_cid == provided_cid
            
        except Exception as e:
            logger.error(f"Error verifying CID: {str(e)}")
            raise HTTPException(status_code=500, detail=str(e))
