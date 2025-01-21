from fastapi import APIRouter

router = APIRouter()

@router.get("/")
async def index():
    return {"message": "Welcome to FuseVault!"}

@router.get("/ping")
async def ping():
    return {"message": "Pong"}
