# FuseVault Frontend

This is the frontend application for FuseVault, a secure digital asset management platform that uses blockchain for verification and IPFS for decentralized storage.

## Features

- **Metamask Authentication**: Secure wallet-based authentication
- **Asset Management**: Create, view, edit, and delete digital assets
- **Blockchain Verification**: Assets are verified using Ethereum blockchain
- **Transaction History**: Track all actions performed on assets
- **User Profile**: Manage user information and preferences

## Technologies Used

- **React**: Frontend framework
- **Material UI**: UI component library
- **React Router**: Client-side routing
- **React Query**: Data fetching and caching
- **Ethers.js**: Ethereum wallet integration
- **Axios**: API communication

## Prerequisites

- Node.js 16+
- npm or yarn
- A web browser with the MetaMask extension installed
- Backend API running (refer to backend README)

## Getting Started

1. Clone the repository
2. Navigate to the frontend directory:

```
cd frontend
```

3. Install dependencies:

```
npm install
```

4. Create a `.env` file in the frontend directory with the following variables:

```
VITE_API_URL=http://localhost:8000
```

5. Start the development server:

```
npm run dev
```

6. Open your browser and navigate to `http://localhost:5173`

## Authentication Flow

1. Click on the "Connect Wallet" button to initiate MetaMask connection
2. MetaMask will prompt you to select an account and connect
3. Click "Sign In" to authenticate with the backend
4. MetaMask will prompt you to sign a message (this is a secure way to prove ownership of the wallet)
5. After signing, you'll be authenticated and redirected to the dashboard

## Building for Production

To create a production build:

```
npm run build
```

The build artifacts will be stored in the `dist/` directory.

## Available Scripts

- `npm run dev` - Run the development server
- `npm run build` - Build for production
- `npm run lint` - Lint the codebase
- `npm run preview` - Preview the production build locally

## Folder Structure

- `src/components/` - Reusable UI components
- `src/contexts/` - React contexts for state management
- `src/hooks/` - Custom React hooks
- `src/pages/` - Page components
- `src/services/` - API service functions
- `src/utils/` - Utility functions