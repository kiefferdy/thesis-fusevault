from fastapi import APIRouter

router = APIRouter()

@router.get("/",
            description="This is the documentation description text for '/' path GET operation.")
async def index():
    return {"message": "Welcome to FuseVault!"}

@router.get("/ping/{pong_str}",
            description="This is the documentation description text for '/ping' path GET operation.")
async def ping(pong_str):
    return {"message": pong_str}