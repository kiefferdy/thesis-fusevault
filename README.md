# FuseVault API

Instructions to run:

- Make sure Python is installed on your computer
- Create a virtual environment with `python -m venv .venv`
- Activate the virtual environment by running `.venv/Scripts/activate`
- Install dependencies with `pip install -r requirements.txt`
- Create a `.env` file in the root project folder, then add the `MONGODB_URI` variable.
- Run the FastAPI server with `uvicorn app.main:app --reload`
- The server is hosted on `http://127.0.0.1:8000/` by default
- Once finished, run `deactivate` to exit the virtual environment

To add dependencies:
- Add the new dependency in a new line to `requirements.in`
- Run `pip-compile requirements.in` (ensure you are in the virtual environment)
- Rerun `pip install -r requirements.txt`
