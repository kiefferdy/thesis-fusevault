from fastapi import APIRouter

router = APIRouter(prefix="/conn", tags=["conn_db_ipfs"])

@router.get("/test")
async def connect():
    """
    Connection Router for MongoDB and IPFS.
    """
    return{"message":"testing router"}