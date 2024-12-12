import os 
from .routers import posts
from fastapi import FastAPI
from dotenv import load_dotenv
from contextlib import asynccontextmanager
from motor.motor_asyncio import AsyncIOMotorClient
from .utils import convert_str_object_id,http_error_handler , preprocess_mongo_doc

env_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),".env")


load_dotenv(dotenv_path=env_path)

MONGO_USER = os.getenv("MONGO_USER")
MONGO_PASSWORD = os.getenv("MONGO_PASSWORD")
MONGO_CLUSTER = os.getenv("MONGO_CLUSTER")
MONGO_DB_NAME = os.getenv("MONGO_DB_NAME")  
MONGO_OPTIONS = os.getenv("MONGO_OPTIONS")


MONGO_URI = f"mongodb+srv://{MONGO_USER}:{MONGO_PASSWORD}@{MONGO_CLUSTER}/{MONGO_DB_NAME}?{MONGO_OPTIONS}"


@asynccontextmanager 
async def lifespan(app:FastAPI) :
    print("Loading resources")
    try :
        app.state.client = AsyncIOMotorClient(MONGO_URI)
        app.state.db = app.state.client.get_database()
        yield
    except Exception as error :
        print(f"Error : {error}")
    finally :
        print("Releasing resources")
        if hasattr(app.state,"client") :
            app.state.client.close()



app = FastAPI(lifespan=lifespan)

app.include_router(posts.router)


