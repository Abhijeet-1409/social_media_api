import jwt
from bson import ObjectId
from app.config import settings
from jwt import InvalidTokenError
from typing import Annotated, Any
from passlib.context import CryptContext
from app.models import TokenData, UserOut
from pymongo.collection import Collection
from fastapi.encoders import jsonable_encoder
from fastapi.security import OAuth2PasswordBearer
from datetime import datetime, timedelta, timezone
from fastapi import Depends, HTTPException, Request, status
from app.utils import preprocess_mongo_doc , convert_str_object_id

settings.secret_key
settings.algorithm 
settings.access_token_expire_minutes


oauth2_scheme = OAuth2PasswordBearer(tokenUrl="login")
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def get_password_hash(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(plain_password,hashed_password) -> bool:
    return pwd_context.verify(plain_password,hashed_password)


async def get_user(request: Request,username: str) -> Any :
    users: Collection = request.app.state.db.users
    user_doc_obj = await users.find_one({"username":username}) 

    if not user_doc_obj :
        return None

    user_json = jsonable_encoder(preprocess_mongo_doc(user_doc_obj))
    user_json["id"] = user_json["_id"]
    user = UserOut(**user_json)
    
    return user


async def authenticate_user(request: Request,username: str,password: str) -> Any :
    user:UserOut  | None = await get_user(request,username)

    if not user :
        return False
    elif not verify_password(password,user.hashed_password) :
        return False 
    
    return user


def create_access_token(data: dict, expires_delta: timedelta | None = None) -> str :
    to_encode = data.copy()
    
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(minutes=15)
    
    to_encode.update({"exp":expire})
    encoded_jwt = jwt.encode(to_encode,settings.secret_key,algorithm=settings.algorithm)
    
    return encoded_jwt


async def get_token_data(request: Request,token: Annotated[str,Depends(oauth2_scheme)]) -> TokenData :
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    try :
        payload: dict = jwt.decode(token,settings.secret_key,algorithms=[settings.algorithm])
        username: str = payload.get("sub")
        user_id: ObjectId | str = payload.get("user_id")

        if username is None or user_id is None or not ObjectId.is_valid(user_id) :
            raise credentials_exception
        
        user_id = convert_str_object_id(user_id)
    
    except InvalidTokenError :
        raise credentials_exception
    
    return TokenData(username=username,user_id=user_id)

async def get_current_user(request: Request,token_data: Annotated[TokenData,Depends(get_token_data)]) -> UserOut :
    
    user: UserOut | None = await get_user(request,token_data.username)
    
    return user


def get_current_active_user(current_user: Annotated[UserOut,Depends(get_current_user)]) ->UserOut :
    
    if current_user.disabled : 
        raise HTTPException(status_code=400, detail="Inactive user")
    
    return current_user