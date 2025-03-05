from typing import List
from fastapi import APIRouter, File, UploadFile, HTTPException
import httpx
from app.utilities.format import format_json

router = APIRouter(prefix="/ipfs", tags=["ipfs"])

WEB3_STORAGE_SERVICE_URL = "http://localhost:8080"

@router.post("/upload-metadata")
async def upload_metadata(metadata: dict):
    """
    Receive metadata as JSON, convert it to a file, and upload it to Web3.Storage.
    Returns the resulting CID.
    """
    try:
        # Format the metadata using the consistent format_json utility
        metadata_json = format_json(metadata)
        
        # Create a file content for direct multipart upload
        multipart_data = [
            ("files", ("metadata.json", metadata_json, "application/json"))
        ]
        
        # Send directly to the web3-storage service
        async with httpx.AsyncClient(timeout=90.0) as client:
            response = await client.post(
                f"{WEB3_STORAGE_SERVICE_URL}/upload",
                files=multipart_data
            )
            response.raise_for_status()

        return {
            "message": "Metadata uploaded successfully",
            "result": response.json()
        }
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error uploading metadata: {str(e)}"
        )

@router.post("/upload")
async def upload_files(files: List[UploadFile] = File(...)):
    """
    Receive multiple file uploads from the client, forward them to the Node web3-storage service,
    and return the resulting CIDs.
    """
    try:
        # Prepare multipart form data for multiple files
        # Each file is a tuple: (form_field_name, (filename, file_bytes, content_type))
        # The form_field_name must match what Node expects ("files" if using upload.array('files')).
        multipart_data = []
        for f in files:
            file_content = await f.read()
            multipart_data.append(
                ("files", (f.filename, file_content, f.content_type))
            )
        
        async with httpx.AsyncClient(timeout=90.0) as client:
            response = await client.post(
                f"{WEB3_STORAGE_SERVICE_URL}/upload",
                files=multipart_data
            )
            response.raise_for_status()

        return response.json()  # e.g. { "cids": [ {"filename": "...", "cid": "..."} ] }

    except httpx.HTTPError as exc:
        raise HTTPException(
            status_code=exc.response.status_code if exc.response else 500,
            detail=f"Error uploading file(s): {str(exc)}"
        )

@router.get("/file/{cid}")
async def get_file_url(cid: str):
    """
    Forwards a GET request to the web3-storage service to retrieve the file URL
    corresponding to the provided CID.
    """
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(f"{WEB3_STORAGE_SERVICE_URL}/file/{cid}")
            response.raise_for_status()
        return response.json()
    except httpx.HTTPError as exc:
        raise HTTPException(
            status_code=exc.response.status_code if exc.response else 500,
            detail=f"Error retrieving file URL: {str(exc)}"
        )

@router.get("/file/{cid}/contents")
async def get_file_contents(cid: str):
    """
    Forwards a GET request to the web3-storage service to retrieve the actual file contents.
    """
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(f"{WEB3_STORAGE_SERVICE_URL}/file/{cid}/contents")
            response.raise_for_status()
        return response.text
    except httpx.HTTPError as exc:
        raise HTTPException(
            status_code=exc.response.status_code if exc.response else 500,
            detail=f"Error retrieving file contents: {str(exc)}"
        )
