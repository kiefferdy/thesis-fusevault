from fastapi import FastAPI
from app.routes.route_sc import router as sc_router
from app.routes.route_db import router as db_router
from app.routes.route_ipfs import router as ipfs_router
from app.routes.route_conn_db_ipfs import router as conn_router
from app.routes.route_conn_sc_ipfs import router as sc_ipfs_route
from app.routes.route_auth import router as auth_router
from app.routes.route_transactions import router as transactions_router

app = FastAPI(title="FuseVault API")

routers = [
    sc_router,
    db_router,
    ipfs_router,
    conn_router,
    sc_ipfs_route,
    auth_router,
    transactions_router
]

for router in routers:
    app.include_router(router)