from typing import Callable, Optional, Dict, Any
import logging
from fastapi import Request, Response, HTTPException
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from app.services.auth_service import AuthService
from app.repositories.auth_repo import AuthRepository
from app.repositories.user_repo import UserRepository
from app.database import get_db_client

logger = logging.getLogger(__name__)

class AuthMiddleware(BaseHTTPMiddleware):
    """
    Middleware to validate authentication for all protected routes.
    Public routes are excluded from authentication checks.
    """
    
    def __init__(self, app):
        """
        Initialize the middleware.
        
        Args:
            app: The FastAPI app
        """
        super().__init__(app)
        # Public routes that don't require authentication
        self.public_paths = [
            "/docs",
            "/redoc",
            "/openapi.json",
            "/auth/login",
            "/auth/validate",
            "/auth/logout",
            "/users/register",
        ]
        # Routes that start with these prefixes are public
        self.public_prefixes = [
            "/docs/",
            "/redoc/",
            "/openapi/",
            "/auth/nonce/",  # Include all nonce endpoints with any wallet address
            # For demo mode and frontend compatibility, include these read-only endpoints
            "/users/",         # Allow accessing user profiles
            "/assets/user/",   # Allow accessing assets
            "/transactions/",  # Allow accessing transactions
            "/transfers/pending/",  # Allow viewing pending transfers
            "/retrieve/",      # Allow retrieving asset metadata
        ]

        # Important: The actual authentication check happens in the route handler for write operations
        
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """
        Dispatch the request and check authentication for protected routes.
        
        Args:
            request: The incoming request
            call_next: The next middleware or route handler
            
        Returns:
            The response from the next middleware or route handler
        """
        # Log the incoming request for debugging
        path = request.url.path
        method = request.method
        logger.info(f"Received {method} request for path: {path}")
        
        # Get session ID from cookies
        cookies = request.cookies
        session_id = cookies.get("session_id")
        logger.debug(f"Cookies: {cookies}")
        logger.debug(f"Session ID: {session_id}")
        
        # Skip authentication for public paths
        if self._is_public_path(path):
            logger.debug(f"Path {path} is public, skipping authentication")
            
            # If this is a "read" operation on one of our data endpoints and there's no session,
            # add a demo mode flag to the request state so endpoints can return appropriate data
            is_read_operation = method == "GET"
            is_data_path = (
                path.startswith("/users/") or 
                path.startswith("/assets/") or 
                path.startswith("/transactions/")
            )
            
            if is_read_operation and is_data_path:
                if not session_id:
                    # Set demo mode flag - handlers can check this to return demo data
                    request.state.demo_mode = True
                    logger.info(f"Demo mode enabled for {path}")
                    
                    # For certain key paths, add placeholder wallet address to help handlers
                    if path.startswith("/users/") or path.startswith("/assets/user/") or path.startswith("/transactions/"):
                        wallet_addr = path.split("/")[2]  # Extract wallet address from path
                        if wallet_addr:
                            request.state.demo_wallet = wallet_addr
                            logger.debug(f"Demo wallet address: {wallet_addr}")
                else:
                    # If we have a session ID, try to validate it for public paths too
                    # This way we can use the real user data for GET requests if authenticated
                    session_data = await self._validate_session(session_id)
                    if session_data:
                        logger.debug(f"Valid session found for public path: {path}")
                        request.state.user = session_data
                        request.state.wallet_address = session_data.get("walletAddress")
                        request.state.demo_mode = False
            
            return await call_next(request)
            
        # Check for session cookie
        if not session_id:
            logger.warning(f"Authentication required for {path} but no session cookie found")
            return JSONResponse(
                status_code=401,
                content={"detail": "Authentication required"}
            )
            
        # Validate session
        session_data = await self._validate_session(session_id)
        if not session_data:
            logger.warning(f"Invalid or expired session for {path}")
            return JSONResponse(
                status_code=401,
                content={"detail": "Invalid or expired session"}
            )
            
        # Add session data to request state for use in route handlers
        request.state.user = session_data
        request.state.wallet_address = session_data.get("walletAddress")
        request.state.demo_mode = False  # Not in demo mode
        logger.info(f"User {session_data.get('walletAddress')} authenticated for {path}")
        
        # Continue processing the request
        return await call_next(request)
        
    def _is_public_path(self, path: str) -> bool:
        """
        Check if a path is public (doesn't require authentication).
        
        Args:
            path: The request path
            
        Returns:
            True if public, False if protected
        """
        # Log the path being checked
        logger.debug(f"Checking if path is public: {path}")
        
        # Check exact matches
        if path in self.public_paths:
            logger.debug(f"Path {path} matched exact public path")
            return True
            
        # Check prefix matches
        for prefix in self.public_prefixes:
            if path.startswith(prefix):
                logger.debug(f"Path {path} matched public prefix: {prefix}")
                return True
        
        logger.debug(f"Path {path} is NOT public")        
        return False
        
    async def _validate_session(self, session_id: str) -> Optional[Dict[str, Any]]:
        """
        Validate a session ID.
        
        Args:
            session_id: The session ID to validate
            
        Returns:
            Session data if valid, None otherwise
        """
        try:
            # Get database client
            db_client = get_db_client()
            
            # Initialize repositories and service
            auth_repo = AuthRepository(db_client)
            user_repo = UserRepository(db_client)
            auth_service = AuthService(auth_repo, user_repo)
            
            # Validate session
            session_data = await auth_service.validate_session(session_id)
            if session_data:
                logger.debug(f"Session validated successfully: {session_id}")
                # Avoid logging detailed session data for privacy/security
                return session_data
            else:
                logger.debug(f"Invalid session ID: {session_id}")
                return None
            
        except Exception as e:
            logger.error(f"Error validating session: {str(e)}")
            return None


# Dependency to get current user from request state
async def get_current_user(request: Request) -> Dict[str, Any]:
    """
    Get the current authenticated user from request state.
    Use this as a dependency in route handlers that need the current user.
    
    Args:
        request: The request object
        
    Returns:
        User data from session
        
    Raises:
        HTTPException: If user is not authenticated
    """
    if not hasattr(request.state, "user") or not request.state.user:
        raise HTTPException(
            status_code=401,
            detail="Authentication required"
        )
        
    return request.state.user
    
# Dependency to get wallet address from request state
async def get_wallet_address(request: Request) -> str:
    """
    Get the wallet address of the current authenticated user.
    Use this as a dependency in route handlers that only need the wallet address.
    
    Args:
        request: The request object
        
    Returns:
        Wallet address
        
    Raises:
        HTTPException: If user is not authenticated
    """
    if not hasattr(request.state, "wallet_address") or not request.state.wallet_address:
        raise HTTPException(
            status_code=401,
            detail="Authentication required"
        )
        
    return request.state.wallet_address