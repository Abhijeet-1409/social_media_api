
from typing import Annotated
from fastapi import APIRouter, Request
from pymongo.collection import Collection
from fastapi.encoders import jsonable_encoder
from fastapi.responses import JSONResponse , Response
from fastapi import status , Body , HTTPException, Path
from ..models import BasePost , PostDatabase , PostUpdate
from ..utils import http_error_handler , preprocess_mongo_doc , convert_str_object_id


router = APIRouter(
    prefix="/posts",
    tags=["Posts"],
)


@router.get("/posts")
@http_error_handler
async def get_posts(request:Request) -> JSONResponse :
    
    posts : Collection = request.app.state.db.posts 
    cursor = posts.find()
    documents = await cursor.to_list(length=None)
    
    post_jsons = [ jsonable_encoder(preprocess_mongo_doc(doc)) for doc in documents ]
    
    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content={"posts" : post_jsons }
    )



@router.post("/posts")
@http_error_handler
async def create_post(request:Request,post: Annotated[BasePost, Body()]) -> JSONResponse :
   
    posts: Collection = request.app.state.db.posts
    post_database = PostDatabase(**post.model_dump())
    post_database_json = jsonable_encoder(post_database)
    result_obj = await posts.insert_one(post_database_json)

    post_doc_obj = await posts.find_one({"_id": result_obj.inserted_id})
    post_json = jsonable_encoder(preprocess_mongo_doc(post_doc_obj))

    return JSONResponse(
        status_code=status.HTTP_201_CREATED,
        content={
            "message": "Post created successfully.",
            "post": post_json,
        }
    )



@router.get("/posts/{id}")
@http_error_handler
async def get_post(request:Request,id:Annotated[str,Path()]) -> JSONResponse :
    
    posts: Collection = request.app.state.db.posts
    object_id = convert_str_object_id(id)  
    post_doc_obj = await posts.find_one({"_id": object_id})
    
    if not post_doc_obj:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Post not found."
        )

    post_json = jsonable_encoder(preprocess_mongo_doc(post_doc_obj))

    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content={"post": post_json}
    )
 


@router.put("/posts/{id}")
@http_error_handler
async def update_post(request:Request,id:Annotated[str,Path()],post_update:Annotated[PostUpdate,Body()]) -> JSONResponse :
   
    posts: Collection = request.app.state.db.posts
    object_id = convert_str_object_id(id)
    post_doc_obj = await posts.find_one({"_id": object_id})

    if not post_doc_obj:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Post not found."
        )

    update_fields = jsonable_encoder(post_update,exclude_unset=True)
   
    update_payload = {"$set": update_fields}

    await posts.update_one({"_id": object_id}, update_payload)
    updated_post_doc = await posts.find_one({"_id": object_id})
    updated_post_json = jsonable_encoder(preprocess_mongo_doc(updated_post_doc))

    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content={
            "message": "Post updated successfully.",
            "post": updated_post_json,
        }
    )



@router.delete("/posts/{id}")
@http_error_handler
async def delete_post(request:Request,id:Annotated[str,Path()]) -> Response :

    posts: Collection = request.app.state.db.posts
    object_id = convert_str_object_id(id)  
    delete_result = await posts.delete_one({"_id": object_id})

    if delete_result.deleted_count == 0:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Post not found."
        )

    return Response(status_code=status.HTTP_204_NO_CONTENT)

