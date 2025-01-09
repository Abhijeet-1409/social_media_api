import uvicorn
from app.config import settings
from asyncio import CancelledError
from app.logger import custom_logger
from app.utils import http_error_handler
from contextlib import asynccontextmanager
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse , JSONResponse
from app.routers import posts , users , auth
from motor.motor_asyncio import AsyncIOMotorClient
from fastapi import FastAPI , HTTPException, status 
from fastapi.middleware.cors import CORSMiddleware
from firebase_admin import credentials, initialize_app , delete_app

@asynccontextmanager
async def lifespan(app: FastAPI):
    custom_logger.info("Loading resources")
    try:
        app.state.client = AsyncIOMotorClient(settings.mongo_uri)
        app.state.db = app.state.client.get_database()
        await app.state.db.users.create_index([("username", 1)], unique=True)

        cred = credentials.Certificate(settings.service_account_json_path)
        app.state.firebase_app = initialize_app(credential=cred)

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
        
        delete_app(app.state.firebase_app)
        
        if hasattr(app.state, "client"):
            app.state.client.close()


app = FastAPI(lifespan=lifespan)
app.mount("/static", StaticFiles(directory="app/static"), name="static")

@app.get("/firebase-messaging-sw.js")
async def service_worker():
    return FileResponse("app/static/js/firebase-messaging-sw.js")

@app.get("/firebaseConfig-and-vapidKey")
@http_error_handler
async def firebase_config_vapidKey():
    vapidKey: str = settings.vapid_key
    firebase_config: dict[str,str] = settings.firebase_clientside_config
    content = {
        'firebaseConfig':firebase_config,
        'vapidKey': vapidKey
    }
    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content=content
    )

app.include_router(auth.router)
app.include_router(users.router)
app.include_router(posts.router)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"], 
    allow_headers=["*"], 
)


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)