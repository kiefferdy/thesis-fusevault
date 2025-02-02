from fastapi import APIRouter, File, UploadFile, HTTPException
import httpx

router = APIRouter(prefix="/ipfs", tags=["ipfs"])

# Base URL of Node.js web3-storage service
WEB3_STORAGE_SERVICE_URL = "http://localhost:8080"

@router.post("/upload")
async def upload_file(file: UploadFile = File(...)):
    """
    Receives a file upload from the client, forwards it to the web3-storage service,
    and returns the resulting CID.
    """
    try:
        file_content = await file.read()
        # Prepare the files payload for the POST request to Node.js
        files = {"file": (file.filename, file_content, file.content_type)}
        async with httpx.AsyncClient() as client:
            response = await client.post(f"{WEB3_STORAGE_SERVICE_URL}/upload", files=files)
            response.raise_for_status()
    except httpx.HTTPError as exc:
        raise HTTPException(
            status_code=exc.response.status_code if exc.response else 500,
            detail=f"Error uploading file: {str(exc)}"
        )
    return response.json()

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
    except httpx.HTTPError as exc:
        raise HTTPException(
            status_code=exc.response.status_code if exc.response else 500,
            detail=f"Error retrieving file URL: {str(exc)}"
        )
    return response.json()

@router.get("/file/{cid}/contents")
async def get_file_contents(cid: str):
    """
    Forwards a GET request to the web3-storage service to retrieve the actual file contents.
    """
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(f"{WEB3_STORAGE_SERVICE_URL}/file/{cid}/contents")
            response.raise_for_status()
    except httpx.HTTPError as exc:
        raise HTTPException(
            status_code=exc.response.status_code if exc.response else 500,
            detail=f"Error retrieving file contents: {str(exc)}"
        )
    return response.text
