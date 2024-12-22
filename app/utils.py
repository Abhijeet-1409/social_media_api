import httpx
from typing import Any
from bson import ObjectId
from functools import wraps
from app.config import settings
from app.logger import custom_logger
from fastapi import HTTPException , status



def convert_to_post_json(post_doc_obj: dict[Any,Any],exclude_id: bool = False) :
    post_json = { key:value for key,value in post_doc_obj.items()}
    post_json["_id"] = str(post_json["_id"])
    post_json["created_at"] = str(post_json["created_at"])
    if exclude_id :
        del post_json["_id"]
    return post_json

def preprocess_mongo_doc(doc:dict[Any,Any]):
    if isinstance(doc, dict):
        return {k: preprocess_mongo_doc(v) for k, v in doc.items()}
    elif isinstance(doc, list):
        return [preprocess_mongo_doc(item) for item in doc]
    elif isinstance(doc, ObjectId):
        return str(doc)
    return doc



def convert_str_object_id(id:Any) :
    if not ObjectId.is_valid(id):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid ID format."
        )
    return  ObjectId(id) 


def http_error_handler(func) :
    @wraps(func)
    async def wrapper(*args, **kwargs) :
        try:
            result = await func(*args, **kwargs)
        except HTTPException as http_exc:
            raise
        except Exception as exc:
            print(exc)
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,detail="Internal Server Error")
        return result
    return wrapper


async def send_single_push_notification(reaction_notification_dic: dict[Any,Any],fcm_token: str) :
    
    url = settings.fcm_url
    fcm_access_token = settings.fcm_access_token

    headers = {
        'Authorization': 'Bearer ' + fcm_access_token,
        'Content-Type': 'application/json; UTF-8',
    }

    title = "User reaction"
    body = f"{reaction_notification_dic['reactor_username']} react {reaction_notification_dic['emoji']} to your post {reaction_notification_dic['post_title']} "

    payload = {
        "to": fcm_token,  
        "notification": {
            "title": title,
            "body": body,
            "sound": "default"
        },
        "priority": "high", 
    }

    async with httpx.AsyncClient() as client:
        try:
            response: httpx.Response = await client.post(url=url, headers=headers, json=payload)
            if 200 <= response.status_code < 300:
                custom_logger.info(f"FCM request succeeded with status code {response.status_code}: {response.text}")
        except httpx.HTTPStatusError as http_error:
            custom_logger.exception(f"FCM request failed with status code {http_error.response.status_code}: {http_error}",stack_info=True)
        except httpx.RequestError as request_error:
            custom_logger.error(f"FCM request failed: {request_error}",stack_info=True)
        except httpx.TimeoutException as timeout_error:
            custom_logger.error(f"FCM request timed out: {timeout_error}",stack_info=True)
        except Exception as e:
            custom_logger.error(f"Unexpected error occurred while sending FCM request: {e}",stack_info=True)

async def send_multiple_push_notification(reaction_notification_doc_list: list[dict[Any,Any]],fcm_token: str):
    
    for reaction_notification_doc in reaction_notification_doc_list :
        
        await send_single_push_notification(
                    fcm_token=fcm_token,
                    reaction_notification_dic=reaction_notification_doc
                )
        
