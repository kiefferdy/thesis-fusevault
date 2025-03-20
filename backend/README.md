# FuseVault Backend

Backend service for the FuseVault digital asset management platform.

## Key Features

- Authentication with Web3/Ethereum signatures
- Asset management with blockchain-backed storage
- Transaction history for all operations
- IPFS integration for decentralized storage
- User management and role-based access control

## Setup Instructions

1. Create and activate virtual environment:
   ```
   python -m venv venv
   # On Windows
   venv\Scripts\activate
   # On macOS/Linux
   source venv/bin/activate
   ```

2. Install dependencies:
   ```
   # For macOS
   pip install -r requirements_mac.txt
   
   # For Windows
   pip install -r requirements_windows.txt
   ```

3. Configure environment variables in `.env` file:
   ```
   MONGODB_URL=mongodb://localhost:27017
   IPFS_API_URL=http://localhost:5001
   INFURA_URL=https://mainnet.infura.io/v3/your-api-key
   ```

4. Start the server:
   ```
   cd backend
   uvicorn app.main:app --reload
   ```

## Troubleshooting

### Diagnosing Backend Issues

Run the diagnostic script to check for common issues:

```
python diagnose.py
```

This will verify:
- If the backend server is running
- If API endpoints are responding correctly
- If CORS headers are properly configured
- Connection between frontend and backend

### Common Issues

#### "Backend Unavailable" Error in Frontend

If you're experiencing "Backend Unavailable" errors in your frontend despite the backend running:

1. Make sure your CORS settings in `app/main.py` include your frontend's origin
2. Verify that your frontend is using the correct API URL (typically `http://localhost:8000`)
3. Check for any Network errors in the browser console
4. Make sure cookies are enabled in your browser (required for session authentication)
5. Use the frontend's debug utilities by opening the browser console and running:
   ```javascript
   window.testBackend()
   window.testCORS()
   window.logCookies()
   ```

#### Authentication Issues

- Ensure that message format in frontend's `AuthContext.jsx` matches exactly with the format in backend's `auth_service.py`
- Make sure MetaMask is installed and connected to the right network
- Check if your session cookie is being properly set (should be visible in browser's dev tools)

## API Documentation

Once running, API documentation is available at:
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc