from fastapi import APIRouter
import app.routes.route_db as db
import app.routes.route_ipfs as ipfs

router = APIRouter(prefix="/conn", tags=["conn_db_ipfs"])

@router.post("/test/{document_id}")
async def receive_doc_db(document_id: str):
    """
    Testing parameter passing between Connection Router and MongoDB Router.
    """
    return await db.get_document(document_id)

@router.post("/test2/{cid}")
async def receive_url_ipfs(cid: str):
    """
    Testing parameter passing between Connection Router and IPFS Router.
    """
    return await ipfs.get_file_contents(cid)