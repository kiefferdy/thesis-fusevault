from typing import Dict, Any, Optional
from fastapi import HTTPException, Response, Request
import logging
from app.services.auth_service import AuthService
from app.schemas.auth_schema import AuthenticationRequest

logger = logging.getLogger(__name__)

class AuthHandler:
    """
    Handler for authentication-related operations.
    Acts as a bridge between API routes and the auth service layer.
    """
    
    def __init__(self, auth_service: AuthService):
        """
        Initialize with auth service.
        
        Args:
            auth_service: Service for authentication operations
        """
        self.auth_service = auth_service
        
    async def get_nonce(self, wallet_address: str) -> Dict[str, Any]:
        """
        Get or generate nonce for a wallet address.
        
        Args:
            wallet_address: The wallet address to get nonce for
            
        Returns:
            Dict containing nonce information
            
        Raises:
            HTTPException: If nonce retrieval fails
        """
        try:
            nonce_response = await self.auth_service.get_nonce(wallet_address)
            
            return {
                "wallet_address": nonce_response.wallet_address,
                "nonce": nonce_response.nonce
            }
            
        except Exception as e:
            logger.error(f"Error getting nonce: {str(e)}")
            raise HTTPException(status_code=500, detail=f"Error getting nonce: {str(e)}")
            
    async def authenticate(
        self,
        request: AuthenticationRequest,
        response: Response
    ) -> Dict[str, Any]:
        """
        Authenticate a user and create a session.
        
        Args:
            request: Authentication request data
            response: FastAPI response object for setting cookies
            
        Returns:
            Dict containing authentication result
            
        Raises:
            HTTPException: If authentication fails
        """
        try:
            # Authenticate
            success, message = await self.auth_service.authenticate(
                wallet_address=request.wallet_address,
                signature=request.signature
            )
            
            if not success:
                raise HTTPException(status_code=401, detail=message)
                
            # Create session
            session_id = await self.auth_service.create_session(request.wallet_address)
            
            if not session_id:
                raise HTTPException(status_code=500, detail="Failed to create session")
                
            # Set session cookie
            response.set_cookie(
                key="session_id",
                value=session_id,
                httponly=True,
                max_age=3600,  # 1 hour
                samesite="lax"
            )
            
            return {
                "status": "success",
                "message": "Authentication successful",
                "wallet_address": request.wallet_address
            }
            
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error authenticating: {str(e)}")
            raise HTTPException(status_code=500, detail=f"Error authenticating: {str(e)}")
            
    async def validate_session(self, request: Request) -> Optional[Dict[str, Any]]:
        """
        Validate a session from a request.
        
        Args:
            request: FastAPI request object
            
        Returns:
            Session data if valid, None otherwise
        """
        try:
            session_id = request.cookies.get("session_id")
            
            if not session_id:
                return None
                
            return await self.auth_service.validate_session(session_id)
            
        except Exception as e:
            logger.error(f"Error validating session: {str(e)}")
            return None
            
    async def logout(self, request: Request, response: Response) -> Dict[str, Any]:
        """
        Log out a user.
        
        Args:
            request: FastAPI request object
            response: FastAPI response object for clearing cookies
            
        Returns:
            Dict containing logout result
            
        Raises:
            HTTPException: If logout fails
        """
        try:
            session_id = request.cookies.get("session_id")
            
            if not session_id:
                raise HTTPException(status_code=401, detail="No active session")
                
            # Invalidate session
            success = await self.auth_service.logout(session_id)
            
            if not success:
                raise HTTPException(status_code=500, detail="Failed to invalidate session")
                
            # Clear session cookie
            response.delete_cookie(key="session_id")
            
            return {
                "status": "success",
                "message": "Logged out successfully"
            }
            
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error logging out: {str(e)}")
            raise HTTPException(status_code=500, detail=f"Error logging out: {str(e)}")
