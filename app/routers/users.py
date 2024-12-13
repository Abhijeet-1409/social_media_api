from typing import Annotated
from ..utils import http_error_handler
from pymongo.collection import Collection
from fastapi.responses import JSONResponse
from pymongo.errors import DuplicateKeyError
from fastapi.encoders import jsonable_encoder
from ..models import UserOut, UserIn,UserDatabase
from ..dependencies import get_current_active_user, get_password_hash
from fastapi import APIRouter, Body, Depends, Request, HTTPException,status

router = APIRouter(
    prefix="/users",
    tags=["Users"],
)

@router.post("") 
@http_error_handler
async def register(request: Request,user_in: Annotated[UserIn,Body()] ) -> JSONResponse:

    user_in_json: dict = jsonable_encoder(user_in)
    hashed_password = get_password_hash(user_in.password)
    user_in_json.update({"hashed_password": hashed_password}) 
    user_db: UserDatabase = UserDatabase(**user_in_json)
    user_db_json: dict = jsonable_encoder(user_db)
    
    try :
        users: Collection = request.app.state.db.users  
        await users.insert_one(user_db_json)
    except DuplicateKeyError as err :
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username is already taken"
        )

    return JSONResponse(
        status_code=status.HTTP_201_CREATED,
        content="User created successfully",
    )

@router.get("/me",response_model=UserOut)
@http_error_handler
async def read_user_me(current_user: Annotated[UserOut, Depends(get_current_active_user)]) -> UserOut :
    return current_user

