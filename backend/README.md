# FuseVault Backend

FastAPI application that serves as the central API for FuseVault. The backend handles authentication, coordinates data across MongoDB/IPFS/blockchain storage layers, and provides REST endpoints for the frontend and API access.

## Technology Stack

- FastAPI with Python 3.9+
- MongoDB with Motor async driver
- Web3.py for Ethereum blockchain interactions
- Pydantic for data validation
- JWT for session management
- Redis for rate limiting (optional)

## Directory Structure

```
app/
├── main.py                 # FastAPI application setup
├── config.py               # Settings and environment configuration
├── database.py             # MongoDB connection and client
├── api/                    # REST API route definitions
│   ├── auth.py            # Authentication endpoints
│   ├── assets.py          # Asset CRUD operations
│   ├── delegation.py      # Delegation management
│   ├── transactions.py    # Transaction history
│   └── api_keys.py        # API key management
├── handlers/               # Request handling logic
│   ├── upload_handler.py  # Asset upload coordination
│   └── auth_handler.py    # Authentication workflows
├── services/               # Business logic layer
│   ├── asset_service.py   # Asset lifecycle management
│   ├── blockchain_service.py # Ethereum contract interactions
│   ├── ipfs_service.py    # IPFS operations via web3-storage
│   ├── transaction_service.py # Audit trail management
│   └── user_service.py    # User management
├── repositories/           # Data access layer
│   ├── asset_repository.py    # MongoDB asset operations
│   ├── transaction_repository.py # Transaction queries
│   └── delegation_repository.py # Delegation data access
├── schemas/                # Pydantic models
│   ├── asset_schemas.py   # Asset request/response models
│   ├── auth_schemas.py    # Authentication schemas
│   └── transaction_schemas.py # Transaction models
└── utilities/              # Helper functions and middleware
    ├── auth_manager.py     # Authentication coordination
    ├── wallet_auth.py      # MetaMask signature verification
    ├── api_key_auth.py     # API key validation
    └── middleware.py       # Request middleware
```

## Setup Instructions

Choose your preferred setup method:

### Option 1: Local Development Setup

#### Prerequisites

- Python 3.9+
- MongoDB running locally or remote connection
- Redis (optional, for rate limiting)
- Web3.Storage service running on port 8080

#### Installation

```bash
# Create virtual environment
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# Install dependencies  
pip install -r requirements.txt

# Copy environment configuration
cp .env.example .env
```

#### Environment Configuration

Configure the `.env` file with these required variables:

```bash
# Database
MONGODB_URI=mongodb://localhost:27017
MONGO_DB_NAME=fusevault

# Blockchain  
WALLET_ADDRESS=0x...                    # Server wallet address
PRIVATE_KEY=0x...                       # Server private key
ALCHEMY_SEPOLIA_URL=https://...         # Sepolia RPC URL
CONTRACT_ADDRESS=0x...                  # Deployed contract address

# JWT Authentication
JWT_SECRET_KEY=your-secret-key          # Minimum 32 characters
JWT_ALGORITHM=HS256
JWT_EXPIRATION_MINUTES=1440

# External Services
WEB3_STORAGE_SERVICE_URL=http://localhost:8080
CORS_ORIGINS=http://localhost:3001

# API Key Authentication (optional)
API_KEY_AUTH_ENABLED=true
API_KEY_SECRET_KEY=your-api-secret      
API_KEY_RATE_LIMIT_PER_MINUTE=100

# Redis (optional)
REDIS_URL=redis://localhost:6379
```

#### Running the Application

```bash
cd backend
uvicorn app.main:app --reload
```

The API will be available at http://localhost:8000

### Option 2: Docker Setup

#### Prerequisites

- Docker and Docker Compose
- Environment configuration (same as Option 1)

#### Using Docker Compose (Recommended)

From the project root directory:

```bash
# Start backend with dependencies (Redis optional)
docker-compose up backend

# Or start all services
docker-compose up
```

#### Individual Container Deployment

```bash
# Build image
docker build -t fusevault-backend .

# Run container
docker run -p 8000:8000 --env-file .env fusevault-backend
```

#### Production Deployment

Use the production docker-compose configuration:

```bash
# From project root
docker-compose -f docker-compose.prod.yml up backend
```

The Docker setup includes:
- Resource limits and health checks
- Hypercorn ASGI server for dual-stack IPv4/IPv6 support
- Non-root user execution for security

## Integration with Other Components

### Frontend Communication
- Provides REST API endpoints consumed by the React frontend
- Handles CORS configuration for browser requests
- Manages user sessions through JWT tokens

### Web3 Storage Service Integration
- Makes HTTP requests to the Node.js IPFS service on port 8080
- Coordinates file uploads and CID calculations
- Handles batch processing and progress tracking

### Blockchain Integration
- Interacts with Ethereum smart contracts via Web3.py
- Manages both client-signed and server-signed transactions
- Queries blockchain for delegation verification and event recovery

### Database Operations
- Uses MongoDB for operational data storage
- Implements repository pattern for clean data access
- Handles complex queries for asset history and transactions

## Testing

```bash
# Run all tests
python -m pytest

# Run specific test file
python -m pytest tests/test_services.py -v

# Run with coverage
python -m pytest --cov=app tests/

# Integration tests
python -m pytest tests/test_integration.py -v
```

## Development Tools

### API Documentation
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc
- OpenAPI spec: http://localhost:8000/openapi.json

### Diagnostics
```bash
# Check service connectivity
python scripts/diagnose.py

# Test database connection
python -c "from app.database import db_client; print(db_client.admin.command('ping'))"
```

## Architecture Patterns

### Service/Repository Pattern
- Services contain business logic
- Repositories handle data access
- Clean separation of concerns

### Dual Authentication
- MetaMask wallet signatures for web users
- API keys for programmatic access
- Context-aware transaction handling

### Request Processing Pipeline
1. Middleware handles authentication
2. Route handlers coordinate operations  
3. Services implement business logic
4. Repositories access data
5. Response formatting and error handling

## Common Development Tasks

### Adding New Endpoints
1. Define route in appropriate `api/` module
2. Create handler function for request processing
3. Implement business logic in service layer
4. Add repository methods if needed
5. Define Pydantic schemas for validation

### Database Migrations
MongoDB is schemaless, but for consistency:
1. Update Pydantic schemas
2. Add repository methods for new fields
3. Consider data migration scripts if needed
