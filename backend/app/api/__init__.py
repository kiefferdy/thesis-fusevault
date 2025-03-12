from app.api.auth_routes import router as auth_router
from app.api.transactions_routes import router as transaction_router
from app.api.upload_routes import router as upload_router
from app.api.users_routes import router as user_router
from app.api.retrieve_routes import router as retrieve_router
from app.api.delete_routes import router as delete_router

__all__ = ["auth_router", "transaction_router", "upload_router", "user_router", "retrieve_router", "delete_router"]
