from datetime import datetime
from typing import Annotated
from pymongo.collection import Collection
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from pymongo.errors import DuplicateKeyError
from fastapi.encoders import jsonable_encoder
from fastapi.responses import JSONResponse 
from pymongo.results import InsertOneResult, UpdateResult 
from app.models import TokenData, UserOut, UserIn,UserDatabase , ActiveUserNotification
from app.dependencies import get_current_active_user, get_password_hash, get_token_data
from fastapi import APIRouter, Body, Depends, Request, HTTPException,status , BackgroundTasks
from app.utils import http_error_handler, send_multiple_push_notification, update_multiple_reaction_notification_doc , validate_fcm_token

router = APIRouter(
    prefix="/users",
    tags=["Users"],
)

templates = Jinja2Templates(directory="app/templates")

@router.post("/notifications/register")
@http_error_handler
async def register_active_user(
    request: Request,
    background_tasks: BackgroundTasks,
    token_data: Annotated[TokenData, Depends(get_token_data)],
    client_id: Annotated[str,Body(...,regex=r'^[0-9a-f]{8}-[0-9a-f]{4}-[0-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$')],
    fcm_token: Annotated[str, Body(...,min_length=10)]
) -> JSONResponse:
    firebase_app = request.app.state.firebase_app
    active_user_notifications: Collection = request.app.state.db.active_user_notifications
    reaction_notifications: Collection = request.app.state.db.reaction_notifications

    # Check for existing active token
    existing_user_doc = await active_user_notifications.find_one(
        {"user_id": token_data.user_id, "fcm_token": fcm_token, "is_active": True,"client_id": client_id,}
    )
    
    if existing_user_doc:
        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content={"message": "FCM token is already registered."},
        )

    await validate_fcm_token (fcm_token=fcm_token,firebase_app=firebase_app)

    # Create new active user document
    active_user: ActiveUserNotification = ActiveUserNotification(
        fcm_token=fcm_token,
        client_id=client_id,
        user_id=token_data.user_id,
        expire_time=token_data.exp,
        username=token_data.username
    )
    active_user_dict: dict = active_user.model_dump()

    result_obj: InsertOneResult = await active_user_notifications.insert_one(active_user_dict)
    if result_obj.inserted_id is None:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to register FCM token."
        )

    # Fetch pending notifications
    cursor = reaction_notifications.find({'recipient_user_id': token_data.user_id, 'sent': False})
    reaction_notification_doc_list: list[dict] = await cursor.to_list(length=10)

    if reaction_notification_doc_list:
        background_tasks.add_task(
            send_multiple_push_notification,
            reaction_notification_doc_list=reaction_notification_doc_list,
            fcm_token=fcm_token,
            client_id=client_id
        )
        background_tasks.add_task(
            update_multiple_reaction_notification_doc,
            reaction_notifications=reaction_notifications,
            reaction_notification_doc_list=reaction_notification_doc_list
        )

    return JSONResponse(
        status_code=status.HTTP_201_CREATED,
        content={"message": "FCM token registered successfully."}
    )




@router.put("/notification/deregister")
@http_error_handler
async def deregister_active_user(
    request: Request,
    token_data: Annotated[TokenData, Depends(get_token_data)],
    client_id: Annotated[str,Body(...,regex=r'^[0-9a-f]{8}-[0-9a-f]{4}-[0-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$')],
    fcm_token: Annotated[str, Body(...,min_length=10)]
) -> JSONResponse:
    update_payload = {"$set": {"is_active": False}}
    active_user_notifications: Collection = request.app.state.db.active_user_notifications

    result_obj: UpdateResult = await active_user_notifications.update_one(
        {
            "user_id": token_data.user_id,
            "fcm_token": fcm_token,
            "is_active": True,
            "client_id": client_id,
        },
        update_payload
    )

    if result_obj.modified_count == 0:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Active FCM token not found or already inactive.",
        )

    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content={"message": "FCM token deregistered successfully."},
    )


@router.get("/notification",response_class=HTMLResponse)
async def notification(request: Request) :
    return templates.TemplateResponse(request=request,name="user_notification.html",context={})


@router.get("/me",response_model=UserOut)
@http_error_handler
async def read_user_me(current_user: Annotated[UserOut, Depends(get_current_active_user)]) -> UserOut :
    return current_user



@router.post("") 
@http_error_handler
async def register(request: Request,user_in: Annotated[UserIn,Body(...)] ) -> JSONResponse:

    user_in_json: dict = jsonable_encoder(user_in)
    hashed_password = get_password_hash(user_in.password)
    user_in_json.update({"hashed_password": hashed_password}) 
    user_db: UserDatabase = UserDatabase(**user_in_json)
    user_db_json: dict = jsonable_encoder(user_db)
    
    try :
        users: Collection = request.app.state.db.users  
        result_obj: InsertOneResult = await users.insert_one(user_db_json)

        if result_obj.inserted_id is None:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to register user."
            )
    
    except DuplicateKeyError as err :
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username is already taken"
        )

    return JSONResponse(
        status_code=status.HTTP_201_CREATED,
        content="User created successfully",
    )
