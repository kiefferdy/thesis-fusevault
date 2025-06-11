# Docker Setup for FuseVault

This guide explains how to run FuseVault using Docker containers.

## Quick Start

1. **Copy environment file:**
   ```bash
   cp .envsample .env
   ```

2. **Edit `.env` file with your configuration:**
   - Add your Web3.Storage DID key and email
   - Add your wallet credentials
   - Add JWT secret keys (minimum 32 characters)
   - Configure other required environment variables

3. **Start all services (development):**
   ```bash
   docker-compose up -d
   ```

4. **Access the application:**
   - Frontend: http://localhost:3001
   - Backend API: http://localhost:8000
   - Web3 Storage Service: http://localhost:8080
   - Database: MongoDB Atlas (external)

## Services

### Backend (FastAPI)
- **Port:** 8000
- **Health Check:** GET http://localhost:8000/docs
- **Dependencies:** MongoDB Atlas, Web3.Storage
- **Runtime:** Python 3.12

### Web3 Storage Service (Node.js)
- **Port:** 8080
- **Dependencies:** Web3.Storage DID authentication
- **Runtime:** Node.js 22 LTS (Alpine)

### Frontend (React)
- **Port:** 3001 (mapped to container port 80)
- **Built with:** Vite + React
- **Served by:** Nginx (production build)
- **Runtime:** Node.js 22 LTS (Alpine) for building

### Database (MongoDB Atlas)
- **External Service:** Hosted on MongoDB Atlas
- **Connection:** Via MONGODB_URI environment variable
- **Database:** fusevault

## Docker Compose Files

This project includes two Docker Compose configurations:

### docker-compose.yml (Development)
- **Purpose:** Local development with hot reloading
- **Features:**
  - Volume mounts for live code editing
  - File watching for auto-restart on changes
  - No resource limits (uses full system resources)
  - Direct access to source code

### docker-compose.prod.yml (Production)
- **Purpose:** Production deployment with optimization
- **Features:**
  - No volume mounts (code baked into images)
  - Resource limits for stability and performance
  - Optimized container configuration
  - Production-ready settings

## Development Workflow

### Hot Reload Development
The development docker-compose includes file watching for hot reloads:

```bash
# Start with file watching
docker-compose up --watch
```

### View Logs
```bash
# All services
docker-compose logs -f

# Specific service
docker-compose logs -f backend
docker-compose logs -f web3-storage
docker-compose logs -f frontend
```

### Rebuild Services
```bash
# Rebuild all services
docker-compose build

# Rebuild specific service
docker-compose build backend
```

### Stop Services
```bash
# Stop all services
docker-compose down

# Stop and remove volumes (WARNING: This deletes database data)
docker-compose down -v
```

## Production Deployment

### Using docker-compose.prod.yml
```bash
# Copy production environment template
cp .envsample .env.prod

# Edit .env.prod with production values
nano .env.prod

# Deploy with production configuration
docker-compose -f docker-compose.prod.yml --env-file .env.prod up -d

# Or use your existing .env file
docker-compose -f docker-compose.prod.yml up -d
```

### Railway Deployment
For Railway deployment, you can deploy each service separately:

1. **Backend:**
   - Point Railway to `./backend` directory
   - Set build command: `docker build -t backend .`
   - Set environment variables in Railway dashboard

2. **Web3 Storage Service:**
   - Point Railway to `./web3-storage-service` directory
   - Set build command: `docker build -t web3-storage .`
   - Set environment variables in Railway dashboard

3. **Frontend:**
   - Point Railway to `./frontend` directory
   - Set build command: `docker build -t frontend .`
   - Update VITE_API_BASE_URL to point to deployed backend

## Environment Variables

See `.envsample` for a complete list of required environment variables.
