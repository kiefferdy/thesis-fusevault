from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import logging

from app.api.auth_routes import router as auth_router
from app.api.transactions_routes import router as transaction_router
from app.api.upload_routes import router as upload_router
from app.api.retrieve_routes import router as retrieve_router
from app.api.users_routes import router as user_router
from app.api.delete_routes import router as delete_router
from app.api.transfer_routes import router as transfer_router
from app.api.assets_routes import router as assets_router
from app.utilities.auth_middleware import AuthMiddleware

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)

# Define lifespan context manager
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: No specific operations yet, but could be added here
    yield
    # Shutdown: Clean up resources
    from app.database import db_client
    if db_client:
        db_client.close()
        logging.info("Database connection closed")

# Create FastAPI app with lifespan
app = FastAPI(
    title="FuseVault API",
    lifespan=lifespan
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",  # React default
        "http://localhost:3001",  # Current Vite config port
        "http://localhost:3002",  # Additional Vite port
        "http://localhost:5173",  # Vite dev server
        "http://localhost:4173",  # Vite preview server
        "http://127.0.0.1:3001",  # Alternative localhost
        "http://127.0.0.1:3002",  # Alternative localhost
        "http://127.0.0.1:5173",  # Alternative localhost
        "http://127.0.0.1:4173",  # Alternative localhost
        "http://127.0.0.1:3000",  # Alternative localhost
    ], 
    allow_credentials=True,
    allow_methods=["*"], 
    allow_headers=["*"],
    expose_headers=["*"]  # Expose headers for cross-origin requests
)

# Add authentication middleware
app.add_middleware(AuthMiddleware)

# Include API routers
api_routers = [
    auth_router,
    transaction_router,
    upload_router,
    retrieve_router,
    user_router,
    delete_router,
    transfer_router,
    assets_router
]

# Add all routers to the app
for router in api_routers:
    app.include_router(router)