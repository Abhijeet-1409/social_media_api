from typing import Annotated
from datetime import timedelta
from app.config import settings
from app.models import UserOut , Token
from fastapi.security import OAuth2PasswordRequestForm
from app.dependencies import authenticate_user, create_access_token
from fastapi import APIRouter, Depends, HTTPException, Request, status

router = APIRouter(tags=["Authenticaiton"])

@router.post("/login",response_model=Token) 
async def login(request: Request,form_data: Annotated[OAuth2PasswordRequestForm,Depends()]) -> Token:
    user: UserOut | bool  = await authenticate_user(request,form_data.username,form_data.password)

    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    access_token_expires = timedelta(minutes=settings.access_token_expire_minutes)
    access_token = create_access_token(
        data={"sub": user.username,"user_id":user.id}, expires_delta=access_token_expires
    )

    return Token(access_token=access_token, token_type="bearer")
