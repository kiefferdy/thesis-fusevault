# FuseVault

FuseVault is a digital asset management platform that uses a hybrid storage approach combining MongoDB, IPFS, and Ethereum blockchain. The system consists of four main components that work together to provide asset storage, authentication, and integrity verification.

## System Architecture

The platform uses a microservice architecture with the following components:

- **Backend (FastAPI)**: Main API server handling business logic, authentication, and data coordination
- **Frontend (React)**: Web interface for user interactions and asset management
- **Web3 Storage Service (Node.js)**: IPFS operations and file storage via Web3.Storage
- **Blockchain (Solidity)**: Smart contracts for ownership verification and delegation

### How Components Interact

1. **Frontend** connects to **Backend** for all user operations
2. **Backend** coordinates data across three storage layers:
   - MongoDB for operational data and queries
   - IPFS (via Web3 Storage Service) for content storage
   - Ethereum blockchain for ownership and integrity verification
3. **Web3 Storage Service** handles IPFS operations independently
4. **Smart contracts** provide the authoritative source of truth for asset ownership

## Directory Structure

```
fusevault/
├── backend/               # FastAPI application
├── frontend/              # React web application  
├── web3-storage-service/  # Node.js IPFS service
├── blockchain/            # Solidity smart contracts
└── README.md             # This file
```

## Prerequisites

- Node.js 18+
- Python 3.9+
- MongoDB
- MetaMask browser extension
- Web3.Storage account

## Setup

Choose your preferred setup method:

### Option 1: Local Development Setup

#### 1. Environment Configuration

Each component needs its own `.env` file. Copy the `.env.example` files in each directory and configure them according to your environment.

#### 2. Backend Setup

```bash
cd backend
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt  # For Windows, use requirements_windows.txt
cp .env.example .env
# Configure your .env file
uvicorn app.main:app --reload
```

The backend will run on http://localhost:8000

#### 3. Web3 Storage Service Setup

```bash
cd web3-storage-service
npm install
cp .env.example .env
# Configure your .env file with Web3.Storage credentials
npm start
```

The service will run on http://localhost:8080

#### 4. Frontend Setup

```bash
cd frontend
npm install
cp .env.example .env
# Configure your .env file
npm run dev
```

The frontend will run on http://localhost:3001

#### 5. Smart Contract Deployment

```bash
cd blockchain
npm install
cp .env.example .env
# Configure your .env file with wallet and RPC details
npx hardhat compile
npx hardhat run scripts/deploy.js --network sepolia
```

Update your backend `.env` file with the deployed contract address.

### Option 2: Docker Setup

#### Quick Start with Docker Compose

```bash
# Configure environment files (same as Option 1)
# Copy .env.example files in each component directory

# Start all services for development
docker-compose up

# Start specific services
docker-compose up backend web3-storage

# Production deployment
docker-compose -f docker-compose.prod.yml up
```

#### Services Included

- **Backend**: FastAPI service with Hypercorn server (port 8000)
- **Frontend**: React app served via Nginx (port 3001)
- **Web3 Storage**: Node.js IPFS service (port 8080)
- **Redis**: Optional caching and rate limiting (development only)

**Note**: You'll still need to deploy smart contracts separately using the blockchain setup commands from Option 1.

## Configuration

Each service requires specific environment variables. See the `.env.example` files in each directory for required configuration:

- **backend/.env**: Database, blockchain, JWT, and service URLs
- **frontend/.env**: Backend API URL
- **web3-storage-service/.env**: Web3.Storage authentication
- **blockchain/.env**: Wallet and RPC configuration

## Running Tests

```bash
# Backend tests
cd backend && python -m pytest

# Frontend tests
cd frontend && npm test

# Smart contract tests
cd blockchain && npx hardhat test
```

## Development Workflow

### Local Development
1. Start MongoDB locally
2. Start the Web3 Storage Service
3. Start the Backend API
4. Start the Frontend development server
5. Deploy smart contracts to testnet
6. Update backend configuration with contract address

### Docker Development
1. Configure environment files
2. Run `docker-compose up` to start all services
3. Deploy smart contracts separately (step 5-6 from local development)

## API Documentation

Once the backend is running, API documentation is available at:
- http://localhost:8000/docs (Swagger UI)
- http://localhost:8000/redoc (ReDoc)

## Authentication

The system supports two authentication methods:
- MetaMask wallet signatures (for web interface)
- API keys (for programmatic access)

Both methods integrate with the blockchain delegation system for permission management.

## Component Documentation

For detailed setup and configuration instructions for each component:

- [Backend README](backend/README.md) - FastAPI service setup and configuration
- [Frontend README](frontend/README.md) - React application development and building
- [Web3 Storage Service README](web3-storage-service/README.md) - IPFS service setup and deployment
- [Blockchain README](blockchain/README.md) - Smart contract deployment and testing
