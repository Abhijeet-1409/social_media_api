import os 

from typing import Annotated
from dotenv import load_dotenv
from .models import Post,PostUpdate
from pymongo.collection import Collection
from contextlib import asynccontextmanager
from motor.motor_asyncio import AsyncIOMotorClient
from fastapi.responses import JSONResponse , Response
from .utils import convert_str_object_id , convert_to_post_json
from fastapi import FastAPI ,status , Body , HTTPException, Path


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

      

@app.get("/posts")
async def get_posts() :
    try :
        posts : Collection = app.state.db.posts 
        cursor = posts.find()
        documents = await cursor.to_list(length=None)
        post_jsons = [ convert_to_post_json(doc) for doc in documents ]
        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content={"posts" : post_jsons }
        )
    except Exception as exc:
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"message": f"An unexpected error occurred: {str(exc)}"}
        )


@app.post("/posts")
async def create_post(post: Annotated[Post, Body()]) -> JSONResponse:
    try:
        posts: Collection = app.state.db.posts
        post_dict = post.model_dump()
        result_obj = await posts.insert_one(post_dict)

        post_doc_obj = await posts.find_one({"_id": result_obj.inserted_id})
        post_json = convert_to_post_json(post_doc_obj)

        return JSONResponse(
            status_code=status.HTTP_201_CREATED,
            content={
                "message": "Post created successfully.",
                "post": post_json,
            }
        )
    except HTTPException as http_exc:
        return JSONResponse(
            status_code=http_exc.status_code,
            content={"message": http_exc.detail}
        )
    except Exception as exc:
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"message": f"An unexpected error occurred: {str(exc)}"}
        )



@app.get("/posts/{id}")
async def get_post(id:Annotated[str,Path()]) :
    try:
        posts: Collection = app.state.db.posts
        
        object_id = convert_str_object_id(id)  
        
        post_doc_obj = await posts.find_one({"_id": object_id})
        
        if not post_doc_obj:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Post not found."
            )
        
        post_json = convert_to_post_json(post_doc_obj)

        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content={"post": post_json}
        )
    except HTTPException as http_exc:
        return JSONResponse(
            status_code=http_exc.status_code,
            content={"message": http_exc.detail}
        )
    except Exception as exc:
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"message": f"An unexpected error occurred: {str(exc)}"}
        )


@app.put("/posts/{id}")
async def update_post(id:Annotated[str,Path()],post_update:Annotated[PostUpdate,Body()]) :
    try :
        posts: Collection = app.state.db.posts

        object_id = convert_str_object_id(id)

        post_doc_obj = await posts.find_one({"_id": object_id})

        if not post_doc_obj:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Post not found."
            )

        update_fields = convert_to_post_json(post_doc_obj,exclude_id=True)

        for key , value in post_update.model_dump(exclude_none=True).items() :
            update_fields[key] = value

        update_payload = {"$set": update_fields}

        await posts.update_one({"_id": object_id}, update_payload)

        updated_post = await posts.find_one({"_id": object_id})
        updated_post_json = convert_to_post_json(updated_post)

        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content={
                "message": "Post updated successfully.",
                "post": updated_post_json,
            }
        )

    except HTTPException as http_exc :
        return JSONResponse(
            status_code=http_exc.status_code,
            content={"message":http_exc.detail}
        )
    except Exception as exc :
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"message": f"An unexpected error occurred: {str(exc)}"}
        )
        


@app.delete("/posts/{id}")
async def delete_post(id:Annotated[str,Path()]) :
    try:
        posts: Collection = app.state.db.posts
        
        object_id = convert_str_object_id(id)  

        delete_result = await posts.delete_one({"_id": object_id})

        if delete_result.deleted_count == 0:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Post not found."
            )

        return Response(status_code=status.HTTP_204_NO_CONTENT)

    except HTTPException as http_exc:
        return JSONResponse(
            status_code=http_exc.status_code,
            content={"message": http_exc.detail}
        )
    except Exception as exc:
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"message": f"An unexpected error occurred: {str(exc)}"}
        )
