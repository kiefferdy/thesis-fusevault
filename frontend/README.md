# MetaMask Authentication Frontend

This is a React-based frontend for authenticating users via MetaMask. It interacts with a FastAPI backend to fetch a nonce, sign it with MetaMask, and verify the signature for authentication.

## Prerequisites

Before running the project, ensure you have the following installed:

- [Node.js](https://nodejs.org/) (16+ recommended)
- [MetaMask](https://metamask.io/) browser extension

## Installation

Navigate to the `frontend` directory and install the required dependencies:

```sh
cd frontend
npm install
```

This will install:

- `react` (Frontend framework)
- `ethers` (For interacting with MetaMask and signing messages)
- `axios` (For making API requests to the backend)

## Running the Project

To start the frontend in development mode:

```sh
npm start
```

Open [http://localhost:3000](http://localhost:3000) to view it in the browser.

### Expected Behavior

1. **Connect MetaMask:** Users will be prompted to connect their MetaMask wallet.
2. **Fetch Nonce:** The frontend requests a nonce from the backend.
3. **Sign Message:** The user signs the nonce message using MetaMask.
4. **Authenticate:** The signed message is sent to the backend for verification.
5. **Success or Failure:** The frontend displays whether authentication was successful.

### Project Structure

```
frontend/
├── src/
│   ├── components/
│   │   ├── MetaMaskLogin.js  # MetaMask authentication component
│   ├── App.js                # Main React App entry
│   ├── index.js              # Renders React app
│   ├── styles.css            # Basic styling
├── package.json              # Project dependencies and scripts
├── README.md                 # This file
```

## Troubleshooting

- If you get a **CORS error**, ensure the backend allows requests from `http://localhost:3000`. In FastAPI, you can use:

  ```python
  from fastapi.middleware.cors import CORSMiddleware

  app.add_middleware(
      CORSMiddleware,
      allow_origins=["*"],  # Adjust this in production
      allow_credentials=True,
      allow_methods=["*"],
      allow_headers=["*"],
  )
  ```

- If MetaMask is not detected, ensure you have the browser extension installed.

- If authentication fails, check the backend logs for errors.

## Notes

- The project assumes a FastAPI backend running at `http://127.0.0.1:8000`.
- The nonce system prevents replay attacks by ensuring each login request is unique.

## Next Steps

- Add UI improvements for better user experience.
- Handle error states more gracefully.
- Secure the authentication process by restricting CORS and enforcing HTTPS in production.

