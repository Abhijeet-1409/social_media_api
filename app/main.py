import uvicorn
from app.config import settings
from asyncio import CancelledError
from app.logger import custom_logger
from contextlib import asynccontextmanager
from app.routers import posts , users , auth
from motor.motor_asyncio import AsyncIOMotorClient
from fastapi import FastAPI , HTTPException, status 


@asynccontextmanager
async def lifespan(app: FastAPI):

    custom_logger.info("Loading resources")
    try:
        app.state.client = AsyncIOMotorClient(settings.mongo_uri)
        app.state.db = app.state.client.get_database()
        await app.state.db.users.create_index([("username", 1)], unique=True)
        yield
    except CancelledError as cancel_error:
        custom_logger.error("Shutdown signal received, cleaning up.")
    except Exception as error:
        custom_logger.error(f"Error initializing resources: {error}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Server is down. Unable to initialize resources."
        )
    finally:
        custom_logger.info("Releasing resources")      
        if hasattr(app.state, "client"):
            app.state.client.close()


app = FastAPI(lifespan=lifespan)

app.include_router(auth.router)
app.include_router(users.router)
app.include_router(posts.router)


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)