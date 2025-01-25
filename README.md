# thesis-fusevault-sc
FuseVault API combines the power of blockchain, IPFS, and traditional storage to mitigate the limitations of on-chain storage while maintaining security and decentralization.


Instructions to run for Windows:

- Make sure Python is installed on your computer
- Create a virtual environment with `python -m venv venv`
- Activate the virtual environment by running `venv/Scripts/activate`
- Install dependencies with `pip install -r requirements.txt`
- Create a `.env` file in the root project folder, then add the `MONGODB_URI` variable
- Run the FastAPI server with `uvicorn app.main:app --reload`
- Access the server on `http://127.0.0.1:8000/` (default setting)
- Once finished, run `deactivate` to exit the virtual environment

Instructions to run for macOS:

- Make sure Python is installed on your computer
- Create a virtual environment with `python3 -m venv venv`
- Activate the virtual environment by running `source venv/bin/activate`
- Install dependencies with `pip install -r requirements.txt`
- Create a `.env` file in the root project folder, then add the `MONGODB_URI` variable
- Install SSL certificates on your system using `/Applications/Python\ 3.x/Install\ Certificates.command` (replace 3.x with your Python version)
- Run the FastAPI server with `uvicorn app.main:app --reload`
- Access the server on `http://127.0.0.1:8000/` (default setting)
- Once finished, run `deactivate` to exit the virtual environment

To view API documentation and execute operation methods:
- Access the server on default url:`http://127.0.0.1:8000/docs` 

To add dependencies:
- Add the new dependency in a new line to `requirements.in`
- Run `pip-compile requirements.in` (ensure you are in the virtual environment)
- Rerun `pip install -r requirements.txt`
