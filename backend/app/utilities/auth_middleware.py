from typing import Callable, Optional, Dict, Any
import logging
from fastapi import Request, Response, HTTPException
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from app.services.auth_service import AuthService
from app.services.auth_manager import AuthManager
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
        # Initialize authentication manager
        self.auth_manager = AuthManager()
        
        # Public routes that don't require authentication
        self.public_paths = [
            "/docs",
            "/redoc",
            "/openapi.json",
            "/auth/login",
            "/auth/validate",
            "/auth/logout",
            "/users/register",
            "/api-keys/create",  # Requires wallet auth, handled in route
            "/api-keys/list",    # Requires wallet auth, handled in route
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
                    # If we have any auth credentials, try to validate them for public paths too
                    # This way we can use the real user data for GET requests if authenticated
                    auth_context = await self.auth_manager.authenticate(request)
                    if auth_context:
                        logger.debug(f"Valid authentication found for public path: {path}")
                        request.state.auth_context = auth_context
                        request.state.wallet_address = auth_context.get("wallet_address")
                        request.state.auth_method = auth_context.get("auth_method")
                        request.state.permissions = auth_context.get("permissions", [])
                        request.state.demo_mode = False
                        
                        # For backward compatibility
                        if auth_context.get("session_data"):
                            request.state.user = auth_context.get("session_data")
            
            return await call_next(request)
            
        # Try to authenticate using the AuthManager (supports multiple methods)
        auth_context = await self.auth_manager.authenticate(request)
        
        if not auth_context:
            logger.warning(f"Authentication required for {path} but no valid credentials found")
            return JSONResponse(
                status_code=401,
                content={"detail": "Authentication required"}
            )
            
        # Add auth context to request state for use in route handlers
        request.state.auth_context = auth_context
        request.state.wallet_address = auth_context.get("wallet_address")
        request.state.auth_method = auth_context.get("auth_method")
        request.state.permissions = auth_context.get("permissions", [])
        request.state.demo_mode = False  # Not in demo mode
        
        # For backward compatibility, also set user if session data is available
        if auth_context.get("session_data"):
            request.state.user = auth_context.get("session_data")
        
        logger.info(f"User {auth_context.get('wallet_address')} authenticated for {path} via {auth_context.get('auth_method')}")
        
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
        # For API key auth, we might not have full user data
        if hasattr(request.state, "auth_context") and request.state.auth_context:
            # Return a minimal user object for API key auth
            return {
                "walletAddress": request.state.auth_context.get("wallet_address"),
                "auth_method": request.state.auth_context.get("auth_method")
            }
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

# New dependency to check permissions
async def check_permission(permission: str):
    """
    Create a dependency that checks for a specific permission.
    
    Args:
        permission: The required permission (read, write, delete, admin)
        
    Returns:
        A dependency function that validates the permission
    """
    async def permission_checker(request: Request) -> Dict[str, Any]:
        if not hasattr(request.state, "auth_context") or not request.state.auth_context:
            raise HTTPException(
                status_code=401,
                detail="Authentication required"
            )
            
        permissions = request.state.auth_context.get("permissions", [])
        
        # Admin permission grants all access
        if "admin" in permissions or permission in permissions:
            return request.state.auth_context
            
        raise HTTPException(
            status_code=403,
            detail=f"Permission denied. Required permission: {permission}"
        )
    
    return permission_checker