from fastapi import FastAPI
from app.routes.route_sc import router as sc_router
from app.routes.route_db import router as db_router
from app.routes.route_ipfs import router as ipfs_router
from app.routes.route_conn_db_ipfs import router as conn_router
from app.routes.route_conn_sc_ipfs import router as sc_ipfs_route


# Initialize FastAPI app
app = FastAPI()

for router in sc_router, db_router, ipfs_router, conn_router, sc_ipfs_route:
    app.include_router(router)