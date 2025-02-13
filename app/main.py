from fastapi import FastAPI
from app.core.route_sc import router as sc_router
from app.core.route_db import router as db_router
from app.core.route_ipfs import router as ipfs_router
from app.connectors.route_conn_db_ipfs import router as db_ipfs_router
from app.connectors.route_conn_sc_ipfs import router as sc_ipfs_route
from app.connectors.route_storage import router as storage_router
from app.external.route_auth import router as auth_router
from app.external.route_transactions import router as transactions_router

app = FastAPI(title="FuseVault API")

routers = [
    sc_router,
    db_router,
    ipfs_router,
    db_ipfs_router,
    sc_ipfs_route,
    auth_router,
    transactions_router,
    storage_router
]

for router in routers:
    app.include_router(router)