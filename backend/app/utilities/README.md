# Authentication System Documentation

## Overview

The FuseVault backend uses a session-based authentication system with the following features:

- Global middleware that protects all routes except explicitly allowed public routes
- Cookie-based session tracking
- Wallet address verification through signature
- Session expiration and extension
- Authenticated user data available in request state

## How Authentication Works

1. **Authentication Flow**:
   - User requests a nonce for their wallet address (`/auth/nonce/{wallet_address}`)
   - User signs the nonce with their wallet private key (on the frontend)
   - User sends the signature to the backend to login (`/auth/login`)
   - Backend verifies the signature and creates a session
   - Session ID is stored in an HTTP-only cookie
   - Each subsequent request includes this cookie automatically
   - Middleware validates the session for each protected request

2. **Session Management**:
   - Sessions expire after a configurable time (default: 1 hour)
   - Sessions are extended on successful validation
   - Logout invalidates the session
   - Session data is stored in MongoDB

## Components

### Auth Middleware (`auth_middleware.py`)

The middleware automatically protects all routes except those explicitly listed as public. It:
- Validates that a session cookie exists
- Validates that the session is active and not expired
- Adds user data to the request state for use in route handlers
- Provides dependencies to easily access the authenticated user data

### Dependencies for Route Handlers

Two main dependencies are available:

1. `get_current_user(request: Request) -> Dict[str, Any]`:
   - Returns the full session data for the authenticated user
   - Raises HTTPException(401) if not authenticated

2. `get_wallet_address(request: Request) -> str`:
   - Returns just the wallet address for the authenticated user
   - Raises HTTPException(401) if not authenticated

## Using Authentication in Routes

### Basic Authentication Protection

The middleware automatically protects all routes. To access authenticated user data, use the dependencies:

```python
from fastapi import APIRouter, Depends, Request
from app.utilities.auth_middleware import get_current_user, get_wallet_address
from typing import Dict, Any

@router.get("/some-protected-endpoint")
async def protected_route(
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    # Access authenticated user data
    wallet_address = current_user.get("walletAddress")
    return {"message": f"Hello, {wallet_address}!"}
```

### Authorization Examples

#### Owner-Based Authorization

For routes that require the user to be a specific wallet owner:

```python
@router.get("/user/{target_wallet_address}/data")
async def get_user_data(
    target_wallet_address: str,
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    # Check if authenticated user is requesting their own data
    authenticated_wallet = current_user.get("walletAddress")
    if authenticated_wallet.lower() != target_wallet_address.lower():
        raise HTTPException(status_code=403, detail="You can only access your own data")
        
    # Continue with data retrieval
    return {"data": "Your protected data"}
```

#### Role-Based Authorization

For routes that require specific user roles (like admin):

```python
@router.get("/admin/users")
async def list_all_users(
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    # Check if user has admin role
    authenticated_role = current_user.get("role", "user")
    if authenticated_role != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")
        
    # Continue with admin operation
    return {"message": "Admin operation successful"}
```

#### Combined Authorization

For routes with flexible permissions (own data or admin access):

```python
@router.put("/users/{wallet_address}")
async def update_user_profile(
    wallet_address: str,
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    # Check if user is updating their own profile or is an admin
    authenticated_wallet = current_user.get("walletAddress")
    authenticated_role = current_user.get("role", "user")
    
    is_own_profile = authenticated_wallet.lower() == wallet_address.lower()
    is_admin = authenticated_role == "admin"
    
    if not (is_own_profile or is_admin):
        raise HTTPException(status_code=403, detail="Not authorized")
        
    # Continue with update operation
    return {"message": "Profile updated successfully"}
```

## Public Routes

The following routes are configured as public (no authentication required):
- `/docs`, `/redoc`, `/openapi.json` - API documentation
- `/auth/nonce/{wallet_address}` - Get a nonce for authentication
- `/auth/login` - Login with a signed nonce
- `/auth/validate` - Validate current session
- `/auth/logout` - Logout endpoint
- `/users/register` - Register a new user


Public routes can be configured in two ways:
1. Exact path matches via the `public_paths` list in `AuthMiddleware.__init__`
2. Prefix matches via the `public_prefixes` list for paths with parameters or nested routes

For example, `/auth/nonce/{wallet_address}` is configured as a prefix match with `/auth/nonce/` to allow any wallet address.

