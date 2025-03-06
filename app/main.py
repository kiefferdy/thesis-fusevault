from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.external.route_auth import router as auth_router
from app.external.route_transactions import router as transactions_router
from app.external.route_sessions import router as session_router
from metamask_auth.route_metamask import router as metamask_router  

app = FastAPI(title="FuseVault API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3001"], 
    allow_credentials=True,
    allow_methods=["*"], 
    allow_headers=["*"],
)

routers = [
    auth_router,
    transactions_router,
    session_router,
    metamask_router
]

for router in routers:
    app.include_router(router)
