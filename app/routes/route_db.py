from fastapi import APIRouter
router = APIRouter()

@router.get("/db")
async def MongoDB():
    return {"message": "Router for MongoDB"}