import os 
from fastapi import FastAPI 
from typing import Annotated
from pydantic import BaseModel
from dotenv import load_dotenv
from motor.motor_asyncio import AsyncIOMotorClient
from contextlib import asynccontextmanager


env_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),".env")


load_dotenv(dotenv_path=env_path)

MONGO_USER = os.getenv("MONGO_USER")
MONGO_PASSWORD = os.getenv("MONGO_PASSWORD")
MONGO_CLUSTER = os.getenv("MONGO_CLUSTER")
MONGO_DB_NAME = os.getenv("MONGO_DB_NAME", "default_db")  
MONGO_OPTIONS = os.getenv("MONGO_OPTIONS")


MONGO_URI = f"mongodb+srv://{MONGO_USER}:{MONGO_PASSWORD}@{MONGO_CLUSTER}/{MONGO_DB_NAME}?{MONGO_OPTIONS}"


class Post(BaseModel) :
    title : str 
    content : str
    published : bool = True


@asynccontextmanager 
async def lifespan(app:FastAPI) :
    try :
        app.state.client = AsyncIOMotorClient(MONGO_URI)
        app.state.db = app.state.client.get_database()
        yield
    except Exception as error :
        print(f"Error : {error}")
    finally :
        app.state.client.close()



app = FastAPI(lifespan=lifespan)


@app.get("/posts")
async def get_posts() :
    return {"message" : "here is all post"}

@app.post("/posts")
async def create_post() :
    return {"message" : "your post is created"}

@app.get("/posts/{id}")
async def get_post(id:int) :
    return {"message" : f"here your post with post id {id}"}

@app.put("/posts/{id}")
async def update_post(id:int) :
    return {"message" : f"your post with post id {id} is updated"}

@app.delete("/posts/{id}")
async def delete_post(id:int) :
    return {"message" : f"your post with post id {id} is deleted"}