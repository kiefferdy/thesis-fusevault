# FuseVault Smart Contracts

Solidity smart contracts that provide blockchain-based asset ownership verification and delegation management for the FuseVault platform. The contracts are deployed on Ethereum Sepolia testnet and integrated with the backend API.

## Purpose

The smart contracts serve as the authoritative source of truth for:

- Asset ownership and version tracking
- User delegation permissions  
- Asset transfer management
- Cryptographic integrity verification

## Technology Stack

- Solidity 0.8.19+
- Hardhat development framework
- Ethers.js for deployment scripts
- Chai for testing

## Directory Structure

```
blockchain/
├── contracts/             # Solidity smart contracts
│   ├── FuseVaultRegistry.sol    # Main asset registry contract
│   └── defunct/           # Legacy contracts
├── scripts/
│   └── deploy.js         # Contract deployment script
├── artifacts/            # Compiled contract artifacts and ABIs
├── cache/                # Hardhat compilation cache
├── hardhat.config.js     # Hardhat configuration
├── package.json          # Dependencies and scripts
└── .env.example          # Environment configuration template
```

## Main Contract: FuseVaultRegistry

The `FuseVaultRegistry.sol` contract handles:

- Asset creation and version management
- IPFS CID storage and verification
- Delegation system for third-party management
- Batch operations for gas optimization
- Asset transfer protocol

### Key Data Structures

```solidity
struct AssetIPFS {
    bytes32 cidHash;        // Keccak256 hash of IPFS CID
    uint32 ipfsVersion;     // Version number
    uint64 lastUpdated;     // Last update timestamp
    uint64 createdAt;       // Creation timestamp
    bool isDeleted;         // Deletion flag
}
```

## Setup Instructions

### Prerequisites

- Node.js 18+
- MetaMask wallet with Sepolia ETH
- Alchemy or Infura RPC endpoint
- Etherscan API key (for verification)

### Installation

```bash
# Install dependencies
npm install

# Copy environment configuration
cp .env.example .env
```

### Environment Configuration

Configure the `.env` file:

```bash
# Wallet Configuration
PRIVATE_KEY=0x...                    # Deployer wallet private key
WALLET_ADDRESS=0x...                 # Deployer wallet address

# Network Configuration
ALCHEMY_SEPOLIA_URL=https://eth-sepolia.g.alchemy.com/v2/...
ETHERSCAN_API_KEY=...                # For contract verification

# Deployment Results (filled after deployment)
CONTRACT_ADDRESS=0x...               # Deployed contract address
```

### Compilation and Testing

```bash
# Compile contracts
npx hardhat compile

# Run test suite
npx hardhat test

# Run tests with gas reporting
npx hardhat test --reporter gas
```

### Deployment

```bash
# Deploy to Sepolia testnet
npx hardhat run scripts/deploy.js --network sepolia

# Verify contract on Etherscan
npx hardhat verify --network sepolia CONTRACT_ADDRESS
```

After deployment, update the backend `.env` file with the contract address.

## Integration with Backend

The FastAPI backend interacts with the deployed contract through Web3.py:

### Backend → Smart Contract
- Asset creation and updates
- Delegation management
- Ownership verification
- Event querying for data recovery

### Contract Events
The contract emits events that the backend monitors:

```solidity
event IPFSUpdated(address indexed owner, string indexed assetId, uint32 ipfsVersion, string cid, bool isDeleted);
event DelegateSet(address indexed owner, address indexed delegate, bool isDelegated);
event TransferInitiated(address indexed from, address indexed to, string indexed assetId);
```

### ABI Integration
The compiled contract ABI is used by the backend for:
- Function call encoding
- Event log decoding  
- Type-safe contract interactions

## Contract Functions

### Asset Management
- `updateIPFS(string assetId, string cid)` - Update asset IPFS hash
- `deleteAsset(string assetId)` - Mark asset as deleted
- `batchUpdateIPFS(string[] assetIds, string[] cids)` - Batch operations

### Verification
- `verifyCID(string assetId, address owner, string cid, uint32 version)` - Verify content integrity
- `getIPFSInfo(string assetId, address owner)` - Get asset information
- `assetExists(string assetId, address owner)` - Check asset existence

### Delegation
- `setDelegate(address delegate, bool isDelegated)` - Set delegation permissions  
- `delegates(address owner, address delegate)` - Check delegation status

### Transfers
- `initiateTransfer(string assetId, address newOwner)` - Start asset transfer
- `acceptTransfer(string assetId, address originalOwner)` - Complete transfer

## Deployment Networks

### Sepolia Testnet
- Network ID: 11155111
- RPC: Alchemy or Infura Sepolia endpoint
- Native token: Sepolia ETH (free from faucets)
- Block explorer: sepolia.etherscan.io

### Configuration for Other Networks
Update `hardhat.config.js` to add additional networks as needed.

## Contract Verification

After deployment, verify the contract on Etherscan:

```bash
npx hardhat verify --network sepolia CONTRACT_ADDRESS
```

This makes the contract source code publicly viewable and enables interaction through the Etherscan interface.
