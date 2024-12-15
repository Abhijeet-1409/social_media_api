import uvicorn
from app.config import settings
from asyncio import CancelledError
from contextlib import asynccontextmanager
from app.routers import posts , users , auth
from motor.motor_asyncio import AsyncIOMotorClient
from fastapi.middleware.cors import CORSMiddleware
from fastapi import FastAPI , HTTPException, status 


@asynccontextmanager
async def lifespan(app: FastAPI):

    print("Loading resources")
    try:
        app.state.client = AsyncIOMotorClient(settings.mongo_uri)
        app.state.db = app.state.client.get_database()
        await app.state.db.users.create_index([("username", 1)], unique=True)
        yield
    except CancelledError as cancel_error:
        print("Shutdown signal received, cleaning up.")
    except Exception as error:
        print(f"Error initializing resources: {error}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Server is down. Unable to initialize resources."
        )
    finally:
        print("Releasing resources")      
        if hasattr(app.state, "client"):
            app.state.client.close()


app = FastAPI(lifespan=lifespan)

origins = ["*"]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(users.router)
app.include_router(posts.router)


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)