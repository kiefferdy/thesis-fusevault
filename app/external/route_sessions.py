from fastapi import APIRouter, HTTPException, Request, Response
from app.core.mongodb_client import MongoDBClient

router = APIRouter(prefix="/sessions", tags=["sessions"])
db_client = MongoDBClient()

SESSION_DURATION = 60

@router.post("/login/{walletAddress}")
async def login(response: Response, walletAddress: str):
    """Login as an existing user using wallet address"""
    try:
        user = db_client.get_user_by_wallet(walletAddress)
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        session_id = db_client.create_session(walletAddress)
        response.set_cookie(key="session_id", value=session_id, httponly=True, max_age=SESSION_DURATION)
        return {"message": "Logged in successfully"}
    except Exception as e:
        raise HTTPException(status_code=401, detail="Invalid credentials")
    
@router.get("/dashboard")
async def dashboard(request: Request):
    """Checks if session is valid using cookies"""
    session_id = request.cookies.get("session_id")
    if not session_id:
        raise HTTPException(status_code=401, detail="Session ID not found in cookies.")
    session = db_client.get_session(session_id)
    if not session:
        raise HTTPException(status_code=401, detail="Session not found or expired.")
    return {"message": f"wallet address: {session['walletAddress']}"}

@router.post("/logout")
async def logout(request: Request, response: Response):
    """Current user logouts and deletes cookies"""
    session_id = request.cookies.get("session_id")
    if session_id:
        db_client.delete_session(session_id)
        response.delete_cookie(key="session_id")
        return {"message": "Logged out successfully"}
    raise HTTPException(status_code=401, detail="No active session to logout.")