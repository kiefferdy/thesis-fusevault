from fastapi import APIRouter
router = APIRouter()

@router.get("/ipfs")
async def IPFS():
    return {"message": "Router for IPFS"}