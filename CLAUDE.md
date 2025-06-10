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
Required environment variables (.env at project root):
- `MONGODB_URI` - MongoDB connection string
- `IPFS_API_URL` - IPFS node endpoint
- `INFURA_URL` - Ethereum node access
- `WEB3_STORAGE_API_TOKEN` - Web3.Storage API key
- `ALCHEMY_SEPOLIA_URL` - Sepolia testnet RPC
- `PRIVATE_KEY` - Deployment wallet private key

## Development Workflow
1. Backend changes: Run tests with `pytest`, ensure handlers/services/repos are tested
2. Frontend changes: Run `npm run lint` before committing
3. Smart contract changes: Run `npx hardhat test` and check gas usage
4. API changes: Update both backend routes and frontend services
5. Always test authentication flow after auth-related changes