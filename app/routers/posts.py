from datetime import datetime
from typing import Annotated
from pymongo.collection import Collection
from app.dependencies import get_token_data
from fastapi.encoders import jsonable_encoder
from fastapi import APIRouter, Depends, Request
from fastapi.responses import JSONResponse , Response
from pymongo.results import InsertOneResult,DeleteResult,UpdateResult
from fastapi import status , Body , HTTPException, Path, BackgroundTasks
from app.models import BasePost , PostDatabase , PostUpdate, TokenData, ReactionInput, Reaction, ReactionNotificaiton
from app.utils import http_error_handler , preprocess_mongo_doc , convert_str_object_id, send_single_push_notification


router = APIRouter(
    prefix="/posts",
    tags=["Posts"],
    dependencies=[Depends(get_token_data)]
)


@router.post("/react/{id}")
@http_error_handler
async def handle_reaction(
    request: Request,
    id: Annotated[str,Path()],
    background_tasks: BackgroundTasks,
    reaction_input: Annotated[ReactionInput,Body(...)],
    token_data: Annotated[TokenData,Depends(get_token_data)]
    ) ->  Response:

    posts: Collection = request.app.state.db.posts
    reactions: Collection = request.app.state.db.reactions
    reaction_notificaion: Collection = request.app.state.db.reaction_notifications
    active_user_notifications: Collection = request.app.state.db.active_user_notifications
    object_id = convert_str_object_id(id)  
    post_doc_obj = await posts.find_one({"_id": object_id})
    

    if not post_doc_obj:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Post not found."
        )
    
    reaction_input_doc = reaction_input.model_dump()
    reaction_input_doc.update({
        "post_id": object_id,
        "reactor_id": token_data.user_id,
        "reactor_username": token_data.username,
        })
    
    reaction_obj: Reaction = Reaction(**reaction_input_doc)
    reaction_obj_doc = reaction_obj.model_dump()

    reaction_result_obj:InsertOneResult = await reactions.insert_one(reaction_obj_doc)

    if reaction_result_obj.inserted_id is None :
        raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to store reacion."
            )

    reaction_obj_doc.update({"recipient_user_id":post_doc_obj['user_id']})
    reaction_notificaion_obj: ReactionNotificaiton = ReactionNotificaiton(**reaction_obj_doc)
    reaction_notificaion_obj_doc = reaction_notificaion_obj.model_dump()
    utc_now = datetime.now(datetime.timezone.utc)

    active_user_doc = await active_user_notifications.find_one({
                            'user_id':post_doc_obj['user_id'],
                            'expire_time':{"$gt":utc_now},
                            'is_active':True
                        })
    
    if active_user_doc :
        reaction_notificaion_obj_doc['sent'] = True
        background_tasks.add_task(
            send_single_push_notification,
            reaction_notification_dic=reaction_notificaion_obj_doc,
            fcm_token=active_user_doc['fcm_token']
            )

    reaction_notificaion_result_obj: InsertOneResult = await reaction_notificaion.insert_one(reaction_notificaion_obj_doc)

    if reaction_notificaion_result_obj.inserted_id is None :
        raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to store reaction notification in the database."
            )

    return Response(status_code=status.HTTP_204_NO_CONTENT)




@router.get("/{id}")
@http_error_handler
async def get_post(request: Request,id: Annotated[str,Path()]) -> JSONResponse :
    
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
 


@router.put("/{id}")
@http_error_handler
async def update_post(
    request:Request,
    id:Annotated[str,Path()],
    post_update:Annotated[PostUpdate,Body(...)],
    token_data: Annotated[TokenData,Depends(get_token_data)]
    ) -> JSONResponse :
   
    posts: Collection = request.app.state.db.posts
    object_id = convert_str_object_id(id)
    post_doc_obj = await posts.find_one({"_id": object_id})

    if not post_doc_obj:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Post not found."
        )

    if post_doc_obj["user_id"] != token_data.user_id :
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You are not authorized to update this post."
        )

    update_fields = jsonable_encoder(post_update,exclude_unset=True)
   
    update_payload = {"$set": update_fields}

    result_obj: UpdateResult = await posts.update_one({"_id": object_id}, update_payload)

    if result_obj.modified_count == 0:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Post was not updated. The provided data may be identical to the current post data.",
        )
    
    updated_post_doc = await posts.find_one({"_id": object_id})
    updated_post_json = jsonable_encoder(preprocess_mongo_doc(updated_post_doc))

    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content={
            "message": "Post updated successfully.",
            "post": updated_post_json,
        }
    )



@router.delete("/{id}")
@http_error_handler
async def delete_post(
    request: Request,
    id: Annotated[str,Path()],
    token_data: Annotated[TokenData,Depends(get_token_data)]
    ) -> Response :

    posts: Collection = request.app.state.db.posts
    object_id = convert_str_object_id(id)  
    post_doc_obj = await posts.find_one({"_id": object_id})

    if not post_doc_obj:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Post not found."
        )

    delete_result: DeleteResult = await posts.delete_one({"_id": object_id,"user_id":token_data.user_id})

    if delete_result.deleted_count == 0:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You are not authorized to delete this post."
        )

    return Response(status_code=status.HTTP_204_NO_CONTENT)



@router.get("")
@http_error_handler
async def get_posts(request: Request) -> JSONResponse : 
    
    posts : Collection = request.app.state.db.posts 
    cursor = posts.find()
    documents = await cursor.to_list(length=None)
    
    post_jsons = [ jsonable_encoder(preprocess_mongo_doc(doc)) for doc in documents ]
    
    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content={"posts" : post_jsons}
    )



@router.post("")
@http_error_handler
async def create_post(
    request: Request,
    post: Annotated[BasePost, Body(...)],
    token_data: Annotated[TokenData,Depends(get_token_data)]
    ) -> JSONResponse :
   
    post_dict: dict = jsonable_encoder(post)
    post_dict.update({"user_id":token_data.user_id})
    post_database: PostDatabase  = PostDatabase(**post_dict)
    
    posts: Collection = request.app.state.db.posts
    post_database_json = post_database.model_dump()
    result_obj: InsertOneResult = await posts.insert_one(post_database_json)

    if result_obj.inserted_id is None:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create the post "
        )

    post_doc_obj = await posts.find_one({"_id": result_obj.inserted_id})
    post_json = jsonable_encoder(preprocess_mongo_doc(post_doc_obj))

    return JSONResponse(
        status_code=status.HTTP_201_CREATED,
        content={
            "message": "Post created successfully.",
            "post": post_json,
        }
    )


    
