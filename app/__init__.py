# app/__init__.py
import os
from dotenv import load_dotenv

# Load environment variables from a .env file
load_dotenv()

# Example: Access an environment variable
MONGO_URI = os.getenv("MONGODB_URI")
