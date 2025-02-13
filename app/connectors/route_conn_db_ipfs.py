from fastapi import APIRouter
import app.core.route_db as db
import app.core.route_ipfs as ipfs

router = APIRouter(prefix="/conn", tags=["conn_db_ipfs"])

@router.post("/upload")
async def upload_content(cid: str):
    """
    Upload retrieved file contents from web3-storage service to MongoDB database.
    """
    text = await ipfs.get_file_contents(cid)
    return await db.upload_json_file(text)