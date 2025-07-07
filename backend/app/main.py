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
from app.api.api_keys_routes import router as api_keys_router
from app.api.blockchain_routes import router as blockchain_router
from app.api.delegation_routes import router as delegation_router
from app.utilities.auth_middleware import AuthMiddleware

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)

# Define lifespan context manager
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: Initialize indexes and other resources
    from app.database import get_db_client
    from app.repositories.api_key_repo import APIKeyRepository
    from app.repositories.user_repo import UserRepository
    from app.repositories.delegation_repo import DelegationRepository
    from app.config import settings
    
    db_client = get_db_client()
    
    try:
        # Initialize user indexes
        user_repo = UserRepository(db_client)
        await user_repo.create_indexes()
        logging.info("User indexes created successfully")
    except Exception as e:
        logging.error(f"Error creating user indexes: {e}")
    
    try:
        # Initialize API key indexes if enabled
        if settings.api_key_auth_enabled:
            api_key_repo = APIKeyRepository(db_client.get_collection("api_keys"))
            await api_key_repo.create_indexes()
            logging.info("API key indexes created successfully")
    except Exception as e:
        logging.error(f"Error creating API key indexes: {e}")
    
    try:
        # Initialize delegation indexes
        delegation_repo = DelegationRepository(db_client)
        await delegation_repo.create_indexes()
        logging.info("Delegation indexes created successfully")
    except Exception as e:
        logging.error(f"Error creating delegation indexes: {e}")
    
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
from app.config import settings
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
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
    assets_router,
    api_keys_router,
    blockchain_router,
    delegation_router
]

# Add all routers to the app
for router in api_routers:
    app.include_router(router)