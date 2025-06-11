# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview
FuseVault is a secure digital asset management platform combining blockchain, IPFS, and traditional storage. It uses microservice architecture with four main components: Backend (FastAPI), Frontend (React), Blockchain (Solidity), and Storage (Web3.Storage).

## Commands

### Backend (FastAPI)
- **Run server**: `cd backend && uvicorn app.main:app --reload`
- **Run all tests**: `cd backend && python -m pytest`
- **Run specific test**: `python -m pytest tests/test_services.py -v`
- **Run with coverage**: `python -m pytest --cov=app tests/`
- **Diagnose connectivity**: `python scripts/diagnose.py`

### Frontend (React)
- **Run dev server**: `cd frontend && npm run dev` (runs on port 3001)
- **Build production**: `npm run build`
- **Lint code**: `npm run lint`
- **Preview build**: `npm run preview`

### Blockchain (Hardhat)
- **Run tests**: `cd blockchain && npx hardhat test`
- **Compile contracts**: `npx hardhat compile`
- **Deploy to Sepolia**: `npx hardhat run scripts/deploy.js --network sepolia`
- **Start local node**: `npx hardhat node`

### Web3 Storage Service
- **Start service**: `cd web3-storage-service && npm start` (runs on port 8080)

## Architecture & Patterns

### Backend Architecture
- **Pattern**: Service/Repository pattern with clear separation of concerns
- **Structure**: 
  - `routes/` - API endpoints following RESTful principles
  - `handlers/` - Request handling and validation
  - `services/` - Business logic
  - `repositories/` - Data access layer
  - `schemas/` - Pydantic models for validation
- **Auth**: MetaMask wallet signature verification via JWT tokens

### Frontend Architecture
- **State Management**: React Query for server state
- **Context**: AuthContext for authentication state
- **Services**: API client pattern in `services/` directory
- **Components**: Reusable components with props validation

### Smart Contracts
- `CIDstorage.sol` - Main contract for IPFS CID storage
- `IPFSVersionRegistry.sol` - Version tracking for assets

## Testing Strategy
- **Backend**: pytest with async support, fixtures in conftest.py
- **Frontend**: Component testing with React Testing Library
- **Blockchain**: Hardhat test framework with Chai assertions
- **Integration**: End-to-end tests in `backend/tests/test_integration.py`

## Code Style Guidelines

### Python (Backend)
- PEP8 compliance
- Type hints for all functions
- snake_case for functions/variables
- CamelCase for classes
- Explicit exception handling

### JavaScript/React (Frontend)
- ES6+ features (arrow functions, destructuring)
- camelCase for variables/functions
- PascalCase for React components
- Function components with hooks
- Named exports for components

### Solidity (Blockchain)
- Follow official Solidity style guide
- Clear function visibility modifiers
- Event emission for state changes

## Environment Setup
Each service has its own .env file for better separation of concerns:

### Backend (.env in backend/ directory):
#### Database Configuration
- `MONGODB_URI` - MongoDB connection string
- `MONGO_DB_NAME` - MongoDB database name (default: fusevault)

#### Blockchain Configuration
- `WALLET_ADDRESS` - Server wallet address for blockchain operations
- `PRIVATE_KEY` - Server wallet private key
- `ALCHEMY_SEPOLIA_URL` - Sepolia testnet RPC URL
- `CONTRACT_ADDRESS` - Deployed smart contract address

#### JWT Configuration
- `JWT_SECRET_KEY` - Secret key for JWT tokens (minimum 32 characters)
- `JWT_ALGORITHM` - JWT algorithm (default: HS256)
- `JWT_EXPIRATION_MINUTES` - JWT token expiration in minutes (default: 1440)

#### Application Configuration
- `DEBUG` - Enable debug mode (default: false)
- `CORS_ORIGINS` - Comma-separated list of allowed frontend origins
- `WEB3_STORAGE_SERVICE_URL` - URL to Web3 Storage service

#### API Key Configuration
- `API_KEY_AUTH_ENABLED` - Enable API key authentication (default: false)
- `API_KEY_SECRET_KEY` - Secret key for API key generation (minimum 32 characters)
- `API_KEY_RATE_LIMIT_PER_MINUTE` - Rate limit per minute for API keys (default: 100)
- `API_KEY_MAX_PER_WALLET` - Maximum API keys per wallet (default: 10)
- `API_KEY_DEFAULT_EXPIRATION_DAYS` - Default API key expiration in days (default: 90)
- `API_KEY_DEFAULT_PERMISSIONS` - Default permissions for new API keys (default: ["read"])

#### Redis Configuration
- `REDIS_URL` - Redis connection URL for rate limiting (optional)

### Web3 Storage Service (.env in web3-storage-service/ directory):
- `WEB3_STORAGE_DID_KEY` - Web3.Storage DID key
- `WEB3_STORAGE_EMAIL` - Email for Web3.Storage authentication

### Frontend (.env in frontend/ directory):
- `VITE_API_URL` - Backend API URL for local development (default: http://localhost:8000)

**Note**: For Docker deployments, the API URL is set via build arguments in docker-compose files, not the .env file.

Use the .env.example files in each directory as templates.

## Development Workflow
1. Backend changes: Run tests with `pytest`, ensure handlers/services/repos are tested
2. Frontend changes: Run `npm run lint` before committing
3. Smart contract changes: Run `npx hardhat test` and check gas usage
4. API changes: Update both backend routes and frontend services
5. Always test authentication flow after auth-related changes