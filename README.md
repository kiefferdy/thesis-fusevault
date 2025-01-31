# FuseVault API

FuseVault API combines the power of blockchain, IPFS, and traditional storage to mitigate the limitations of on-chain storage while maintaining security and decentralization.

## Running the API

### For Windows:
- Make sure Python is installed on your computer
- Create a virtual environment with `python -m venv venv`
- Activate the virtual environment by running `venv/Scripts/activate`
- Install dependencies with `pip install -r requirements.txt`
- Create a `.env` file in the root project folder, then add the [required environment variables](#required-environment-variables)
- Run the FastAPI server with `uvicorn app.main:app --reload`
- Access the server on `http://127.0.0.1:8000/` (default setting)
- Once finished, run `deactivate` to exit the virtual environment

### For macOS:
- Make sure Python is installed on your computer
- Create a virtual environment with `python3 -m venv venv`
- Activate the virtual environment by running `source venv/bin/activate`
- Install dependencies with `pip install -r requirements.txt`
- Create a `.env` file in the root project folder, then add the [required environment variables](#required-environment-variables)
- Install SSL certificates on your system using `/Applications/Python\ 3.x/Install\ Certificates.command` (replace 3.x with your Python version)
- Run the FastAPI server with `uvicorn app.main:app --reload`
- Access the server on `http://127.0.0.1:8000/` (default setting)
- Once finished, run `deactivate` to exit the virtual environment

### To view API documentation and execute operation methods:
- Access the server on default URL: `http://127.0.0.1:8000/docs`

### To add dependencies:
- Add the new dependency in a new line to `requirements.in`
- Run `pip-compile requirements.in` (ensure you are in the virtual environment)
- Rerun `pip-sync requirements.txt`

## Running the Web3.Storage Microservice
- Make sure Node.js is installed on your computer
- Navigate to the `web3-storage-service/` directory
- Install dependencies with `npm install`
- Create a `.env` file in the root project folder, then add the [required environment variables](#required-environment-variables)
- Run the microservice with `npm run start`
- Access the microservice on `http://127.0.0.1:8080/` (default setting)

## Deploying the Smart Contract

Follow these steps to deploy the smart contract:

1. Download MetaMask.

2. Set up your MetaMask wallet:
   - Switch to the Sepolia Testnet in your MetaMask settings.
   - Export your private key:
     - Go to your wallet settings → Security & Privacy → Export Private Key.
     - Copy your private key.

3. Set up the `.env` file with the [required environment variables](#required-environment-variables).

4. Open Remix IDE:
   - In the Deploy & Run Transactions panel:
     - Choose **Injected Provider - MetaMask** as your environment.
     - Ensure your MetaMask wallet is connected.

5. Open `CIDstorage.sol`:
   - Save it and then deploy
   - Retrieve the Contract Address (After deployment, expand the deployed contract in Remix IDE)

6. Copy the contract address and paste it into your `.env` file.

7. Start the server with `uvicorn app.main:app --reload`.

**Note to Thesis Team**: If you'd prefer to use the pre-deployed smart contract, use the discussed `.env` variables.

## Required Environment Variables

```env
MONGO_URI=[Insert MongoDB URI]
WALLET_ADDRESS=[Insert your MetaMask wallet address]
PRIVATE_KEY=[Insert your private key]
INFURA_URL=[Insert the Infura URL]
CONTRACT_ADDRESS=[Insert the smart contract address]
WEB3_STORAGE_DID_KEY=[Insert the Web3.Storage DID key]
WEB3_STORAGE_EMAIL=[Insert the Web3.Storage account email]
