# FuseVault Frontend

React web application that provides the user interface for FuseVault digital asset management. The frontend handles user authentication through MetaMask and communicates with the backend API for all asset operations.

## Technology Stack

- React 18 with hooks
- Material-UI for components
- React Query for server state management
- Ethers.js for Ethereum wallet interactions
- React Router for navigation
- Axios for HTTP requests

## Directory Structure

```
src/
├── App.jsx                 # Main application component
├── index.js               # Application entry point
├── components/            # Reusable UI components
│   ├── AssetCard.jsx     # Individual asset display
│   ├── AssetGrid.jsx     # Asset list view
│   ├── BatchProgress.jsx # Upload progress tracking
│   └── TransactionHistory.jsx # Transaction display
├── contexts/
│   └── AuthContext.jsx   # Global authentication state
├── hooks/
│   └── useAssets.js      # React Query hooks for assets
├── pages/                # Route components
│   ├── Dashboard.jsx     # Main asset dashboard
│   ├── Upload.jsx        # Asset upload interface
│   ├── AssetDetail.jsx   # Individual asset view
│   ├── AssetHistory.jsx  # Asset version history
│   ├── ApiKeys.jsx       # API key management
│   ├── Delegation.jsx    # Permission management
│   └── TransactionHistory.jsx # Full transaction log
├── services/             # API communication
│   ├── authService.js    # Authentication APIs
│   ├── assetService.js   # Asset management APIs
│   ├── delegationService.js # Delegation APIs
│   └── apiClient.js      # HTTP client configuration
└── utils/
    ├── validation.js     # Form validation helpers
    └── formatting.js     # Data formatting utilities
```

## Setup Instructions

Choose your preferred setup method:

### Option 1: Local Development Setup

#### Prerequisites

- Node.js 18+
- Backend API running on port 8000
- MetaMask browser extension

#### Installation

```bash
# Install dependencies
npm install

# Copy environment configuration
cp .env.example .env

# Start development server
npm run dev
```

The application will be available at http://localhost:3001

#### Environment Configuration

Create a `.env` file with:

```bash
VITE_API_URL=http://localhost:8000
```

### Option 2: Docker Setup

#### Prerequisites

- Docker and Docker Compose
- Backend API (can be started via Docker as well)
- MetaMask browser extension

#### Using Docker Compose (Recommended)

From the project root directory:

```bash
# Start frontend with backend dependencies
docker-compose up frontend

# Or start all services
docker-compose up
```

#### Individual Container Deployment

```bash
# Build image with API URL
docker build --build-arg VITE_API_URL=http://localhost:8000 -t fusevault-frontend .

# Run container
docker run -p 3001:80 fusevault-frontend
```

#### Production Deployment

Use the production docker-compose configuration:

```bash
# From project root
docker-compose -f docker-compose.prod.yml up frontend
```

The Docker setup includes:
- Multi-stage build for optimized production images
- Nginx server with gzip compression and caching
- Health checks and non-root user execution
- Build-time API URL configuration

**Note**: For production builds, the API URL is set through build arguments rather than environment files.

## Integration with Backend

The frontend communicates with the FastAPI backend through REST endpoints:

- Authentication: `/auth/` routes for wallet verification and session management
- Assets: `/assets/` routes for CRUD operations and batch processing  
- Delegation: `/delegation/` routes for permission management
- Transactions: `/transactions/` routes for history and auditing
- API Keys: `/api-keys/` routes for programmatic access management

## Authentication Flow

1. User clicks "Connect Wallet" to initiate MetaMask connection
2. Frontend requests authentication nonce from backend
3. User signs message in MetaMask containing the nonce
4. Frontend submits signature to backend for verification
5. Backend validates signature and creates session
6. Frontend stores authentication state and enables protected routes

## Available Scripts

```bash
npm run dev      # Start development server
npm run build    # Build for production  
npm run preview  # Preview production build
npm run lint     # Run ESLint
npm test         # Run test suite
```

## Key Components

### Authentication (AuthContext)
- Manages wallet connection state
- Handles MetaMask interactions
- Stores user session information
- Provides authentication state to all components

### Asset Management
- **AssetDashboard**: Main interface showing user's assets
- **Upload**: Single and batch asset creation
- **AssetDetail**: Individual asset information and operations
- **AssetHistory**: Version tracking and audit trail

### Progress Tracking
- Real-time upload progress through multiple stages
- Batch operation status with individual item tracking
- Error handling and retry mechanisms

### API Integration
- React Query for server state management and caching
- Axios interceptors for request/response handling
- Automatic authentication token management
