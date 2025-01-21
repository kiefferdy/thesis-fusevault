from fastapi import FastAPI
from contextlib import asynccontextmanager
from motor.motor_asyncio import AsyncIOMotorClient
from app.routes.routes import router as main_router
from app import MONGO_URI

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Create and store the MongoDB client in app.state
    app.state.client = AsyncIOMotorClient(MONGO_URI)
    app.state.db = app.state.client["Fusevault"]

    # Test the connection
    await app.state.client.admin.command("ping")
    print("Successfully connected to MongoDB!")

    try:
        yield
    finally:
        # Attempt to close the client if it still exists
        client = getattr(app.state, "client", None)
        if client is not None:
            print("Closing MongoDB connection...")
            client.close()
            app.state.client = None
            app.state.db = None
            print("Closed MongoDB connection.")

app = FastAPI(lifespan=lifespan)
app.include_router(main_router)
