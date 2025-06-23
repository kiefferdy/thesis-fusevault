# Test Data for FuseVault Batch Upload

This directory contains sample files for testing the batch upload functionality of FuseVault.

## File Types

### JSON Files (Individual Assets)
Each JSON file represents a single asset. Multiple JSON files can be selected for batch upload.

#### Format Options
The system accepts both camelCase and snake_case field names:

**camelCase format:**
```json
{
  "assetId": "unique-asset-id",
  "walletAddress": "0x742d35Cc6643C0532925a3b8A9C2E7E7c18e1234",
  "criticalMetadata": {
    "name": "Asset Name",
    "description": "Asset description",
    "category": "documents"
  },
  "nonCriticalMetadata": {
    "fileSize": "1.5MB",
    "author": "John Doe"
  }
}
```

**snake_case format:**
```json
{
  "asset_id": "unique-asset-id", 
  "wallet_address": "0x742d35Cc6643C0532925a3b8A9C2E7E7c18e1234",
  "critical_metadata": {
    "name": "Asset Name",
    "description": "Asset description", 
    "category": "documents"
  },
  "non_critical_metadata": {
    "file_size": "1.5MB",
    "author": "John Doe"
  }
}
```

#### Required Fields
- `assetId` or `asset_id`: Unique identifier for the asset
- `criticalMetadata` or `critical_metadata`: Core data stored on blockchain

#### Optional Fields  
- `walletAddress` or `wallet_address`: Owner's wallet (defaults to current user)
- `nonCriticalMetadata` or `non_critical_metadata`: Additional data stored only in database

### CSV Files (Batch Assets)
CSV files contain multiple assets in tabular format.

#### Required Columns
- `asset_id`: Unique identifier for each asset
- `wallet_address`: Ethereum wallet address of the asset owner

#### Critical vs Non-Critical Fields
When uploading CSV files, you specify which columns should be treated as "critical metadata" (stored on blockchain). All other columns become "non-critical metadata" (stored only in database).

## Sample Files

### JSON Files
- `asset_001_company_logo.json` - Company branding asset
- `asset_002_financial_report.json` - Financial document  
- `asset_003_smart_contract.json` - Blockchain smart contract
- `asset_004_product_photo.json` - E-commerce product image
- `asset_005_legal_contract.json` - Legal document/NDA
- `asset_006_research_data.json` - Research dataset

### CSV Files
- `batch_assets_sample.csv` - Comprehensive sample with 8 assets of various types
- `simple_assets.csv` - Simple 5-asset sample for basic testing

## Testing Instructions

### JSON Batch Upload
1. Go to Upload page → "Batch Upload" tab
2. Select "JSON" format
3. Choose multiple JSON files from this directory
4. Click "Upload Files"
5. Sign the MetaMask transaction (for wallet users)

### CSV Batch Upload  
1. Go to Upload page → "Batch Upload" tab
2. Select "CSV" format
3. Choose a CSV file (`batch_assets_sample.csv` or `simple_assets.csv`)
4. Specify critical fields (e.g., `name,description,category` for sample files)
5. Click "Upload Files"
6. Sign the MetaMask transaction (for wallet users)

## Critical Fields Examples

For the provided CSV files, good choices for critical fields are:

**batch_assets_sample.csv:**
- `name,description,assetType,category`
- `name,category,confidentialityLevel`

**simple_assets.csv:**
- `name,description,category`
- `name,category,priority,status`

## Wallet Addresses

The sample files use several test wallet addresses:
- `0x742d35Cc6643C0532925a3b8A9C2E7E7c18e1234`
- `0x987fcdeb51294a13f58a487b8e5c6789def01234` 
- `0x456789abcdef0123456789abcdef0123456789ab`
- `0x111222333444555666777888999aaabbbcccddee`

**Note:** These are example addresses. Replace with actual wallet addresses for real testing.

## Batch Size Limits

- Maximum 50 assets per batch upload
- This applies to both JSON file collections and CSV rows

## Authentication Methods

Both wallet authentication (MetaMask) and API key authentication are supported:

- **Wallet Auth**: User signs transaction, assets owned by user's wallet
- **API Key Auth**: Server signs transaction, but assets still owned by user's wallet (requires delegation)