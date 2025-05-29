# FuseVault Project Commands & Styles

## Commands
- **Frontend**: `cd frontend && npm run dev` (run), `npm run build` (build), `npm run lint` (lint)
- **Backend**: `cd backend && python -m pytest` (all tests), `python -m pytest tests/test_services.py -v` (specific test file)
- **Blockchain**: `cd blockchain && npx hardhat test` (test), `npx hardhat run scripts/deploy.js --network sepolia` (deploy)
- **Web3 Storage**: `cd web3-storage-service && npm start` (run service)

## Code Style
- **Python**: Use PEP8, snake_case for functions/variables, CamelCase for classes
- **JavaScript**: Use ES6+ features, camelCase for variables/functions, PascalCase for components
- **React**: Function components with hooks preferred, use named exports
- **Types**: Strong typing in Python (using type hints), PropTypes in React components
- **Error Handling**: Use try/catch in JS, explicit exception handling in Python
- **Testing**: Write unit tests for all services, handlers, and repositories

## Architecture
- Microservice architecture: Backend (FastAPI), Frontend (React), Blockchain (Solidity), Storage (Web3.Storage)
- Follow RESTful API design principles in backend routes
- Use service/repository pattern for separation of concerns