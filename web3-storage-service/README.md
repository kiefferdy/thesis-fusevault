# Web3 Storage Service

Node.js Express service that handles IPFS operations through Web3.Storage. This service exists as a separate component because the Web3.Storage W3UP client library is only available for Node.js, while the main backend is built with Python.

## Purpose

The service provides IPFS functionality to the FastAPI backend by:

- Uploading files to IPFS via Web3.Storage
- Computing Content Identifiers (CIDs) for change detection
- Retrieving files from IPFS gateways  
- Managing temporary file storage and cleanup

## Technology Stack

- Node.js 18+ with Express
- W3UP client library for Web3.Storage
- Multer for file upload handling
- UUID for temporary file naming

## Directory Structure

```
web3-storage-service/
├── index.js              # Express server and route definitions
├── backend.js             # Web3.Storage client configuration
├── utilities.js           # CID calculation helpers
├── upload_queue/          # Temporary file storage directory
├── test.js               # Basic functionality testing
├── package.json          # Dependencies and scripts
├── .env.example          # Environment configuration template
└── Dockerfile            # Container deployment
```

## Setup Instructions

Choose your preferred setup method:

### Option 1: Local Development Setup

#### Prerequisites

- Node.js 18+
- Web3.Storage account and credentials

#### Installation

```bash
# Install dependencies
npm install

# Copy environment configuration
cp .env.example .env

# Configure your Web3.Storage credentials in .env

# Start the service
npm start
```

The service will run on http://localhost:8080

#### Environment Configuration

Create a `.env` file with Web3.Storage authentication:

```bash
# Primary authentication method (recommended)
W3_PRINCIPAL=did:key:...    # Web3.Storage DID principal
W3_PROOF=...                # Delegation proof token

# Alternative authentication (development)
WEB3_STORAGE_DID_KEY=...    # Legacy DID key format
WEB3_STORAGE_EMAIL=...      # Email for development setup

# Service configuration
PORT=8080
NODE_ENV=production
```

### Option 2: Docker Setup

#### Prerequisites

- Docker and Docker Compose
- Environment configuration (same as Option 1)

#### Using Docker Compose (Recommended)

From the project root directory:

```bash
# Start web3-storage service
docker-compose up web3-storage

# Or start all services
docker-compose up
```

#### Individual Container Deployment

```bash
# Build image
docker build -t web3-storage-service .

# Run container
docker run -p 8080:8080 --env-file .env web3-storage-service
```

#### Production Deployment

Use the production docker-compose configuration:

```bash
# From project root
docker-compose -f docker-compose.prod.yml up web3-storage
```

The Docker setup includes:
- Node.js 22 Alpine base image
- Health checks and non-root user execution
- Automatic temporary file cleanup
- IPv6 support for Railway deployment

## Integration with Backend

The FastAPI backend communicates with this service via HTTP requests:

### Backend → Web3 Storage Service
- `POST /upload` - Upload files to IPFS
- `POST /calculate-cid` - Compute CID without storing
- `GET /file/:cid` - Get gateway URLs for content
- `GET /file/:cid/contents` - Retrieve file contents
- `GET /health` - Service health check

### Request Flow
1. Backend receives file upload request
2. Backend forwards files to Web3 Storage Service
3. Service uploads to IPFS and returns CID
4. Backend stores CID in MongoDB and blockchain
5. Service cleans up temporary files

## API Endpoints

### File Upload
```http
POST /upload
Content-Type: multipart/form-data
```

Accepts single or multiple files and returns IPFS CIDs.

### CID Calculation  
```http
POST /calculate-cid
Content-Type: multipart/form-data
```

Calculates what the CID would be without actually storing to IPFS.

### File Retrieval
```http
GET /file/:cid
GET /file/:cid/contents
```

Returns gateway URLs or fetches content directly.

### Health Check
```http
GET /health
```

Returns service status and timestamp.

## File Processing

### Temporary File Handling
- Files stored in `upload_queue/` with UUID names
- Automatic cleanup on success or failure
- No persistent storage of user content

### Batch Processing
- Supports multiple files in single request
- Dynamic timeout scaling based on file count
- Individual file status tracking

## Available Scripts

```bash
npm start         # Start production server
npm run dev       # Development mode with auto-reload
npm test         # Run basic functionality tests
```
