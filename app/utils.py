import httpx
import asyncio
from typing import Any
from bson import ObjectId
from functools import wraps
from app.config import settings
from app.logger import custom_logger
from pymongo.results import UpdateResult 
from pymongo.collection import Collection
from fastapi import HTTPException , status
from concurrent.futures import ThreadPoolExecutor
from firebase_admin.exceptions import FirebaseError
from firebase_admin import messaging ,credentials, initialize_app 

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
            custom_logger.error(f"Unexpected error occurred while sending FCM request: {exc}",stack_info=True)
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,detail="Internal Server Error")
        return result
    return wrapper



def send_fcm_message(fcm_token: str,firebase_app: Any):
    
    try :
        message = messaging.Message(
                notification=messaging.Notification(
                    title="User reaction",
                    body="Random user likey your post."
                ),
                data={
                    "client_id": "eff78a02-a36b-46c4-9888-886617b187c4",
                },
                token=fcm_token,
            )

        response = messaging.send(message=message,dry_run=True,app=firebase_app)
        custom_logger.info(response)
    
    except FirebaseError as exc :   
        http_response_json = exc.http_response.json()
        code = http_response_json['error']['code']
        error_message = http_response_json['error']['message']
        raise HTTPException(
            status_code=code,
            detail=error_message
        )
    
    except Exception as exc :
        custom_logger.error(f"Unexpected error occured {exc}",stack_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        )


async def validate_fcm_token(fcm_token:str,firebase_app:Any):

    try :
        response = await asyncio.to_thread(send_fcm_message, fcm_token, firebase_app)

    except HTTPException as httpexc :
        raise httpexc
    
    except Exception as exc:
        custom_logger.error(f"Unexpected error in validate_fcm_token: {exc}", stack_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error while validating FCM token"
        ) 
    


async def send_single_push_notification(reaction_notification_dic: dict[Any,Any],fcm_token: str,client_id: str) :
    
    url = settings.fcm_url
    fcm_access_token = await settings.fcm_access_token

    headers = {
        'Authorization': 'Bearer ' + fcm_access_token,
        'Content-Type': 'application/json; UTF-8',
    }

    title = "User reaction"
    body = f"{reaction_notification_dic['reactor_username']} react {reaction_notification_dic['emoji']} to your post {reaction_notification_dic['post_title']}"


    payload = {
        "message": {
            "token": fcm_token,
            "notification": {
                    "title": title,
                    "body": body
            },
            "data": {
                "clientId": client_id
            }
        }      
    }

    async with httpx.AsyncClient() as client:
        try:
            response: httpx.Response = await client.post(url=url, headers=headers, json=payload)
            response.raise_for_status()
            if 200 <= response.status_code < 300:
                custom_logger.info(f"FCM request succeeded with status code {response.status_code} for reaction notification id :{reaction_notification_dic['_id']}")
        
        except httpx.HTTPStatusError as http_error:
            custom_logger.error(f"FCM request failed with status code {http_error.response.status_code}: {http_error}")
        
        except Exception as exc:
            custom_logger.exception(f"Unexpected error occurred while sending FCM request: {exc}",stack_info=True)


async def send_multiple_push_notification(reaction_notification_doc_list: list[dict[Any,Any]],fcm_token: str,client_id: str):
    
    tasks: list[asyncio.Task] = []

    for reaction_notification_doc in reaction_notification_doc_list :
        
       tasks.append(asyncio.create_task(send_single_push_notification(
                    fcm_token=fcm_token,
                    reaction_notification_dic=reaction_notification_doc,
                    client_id=client_id
                )))
       
    await asyncio.gather(*tasks)


async def update_multiple_reaction_notification_doc(reaction_notifications: Collection,reaction_notification_doc_list: list[dict[Any,Any]]) :
    try :
        ids_to_update_list: list[ObjectId] = [reaction_notification_doc['_id'] for reaction_notification_doc in reaction_notification_doc_list]
        result_obj: UpdateResult = await reaction_notifications.update_many(
            { "_id": { "$in": ids_to_update_list } }, 
            { "$set": { "sent": "True" } } 
        )

        if result_obj.modified_count == len(ids_to_update_list) :
            custom_logger.info(f"All reaction notification is updated")
        else :
            custom_logger.info(f"Few reaction notification not updated")

    except Exception as exc :
        custom_logger.error(f"Exception occured during update of multiple reaction notification docs : {exc}",stack_info=True)


async def main() :
    cred = credentials.Certificate(settings.service_account_json_path)
    firebase_app = initialize_app(credential=cred)
    fcm_token = input("fcm_token:")
    try :
        await validate_fcm_token(fcm_token=fcm_token,firebase_app=firebase_app)
    except HTTPException as http_exc :
        custom_logger.info(http_exc)
    except Exception as exc :
        custom_logger.error(exc,stack_info=True)


if __name__ == "__main__" :
    asyncio.run(main())