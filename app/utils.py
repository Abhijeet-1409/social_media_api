from functools import wraps
from bson import ObjectId
from fastapi import HTTPException , status


def convert_to_post_json(post_doc_obj,exclude_id=False) :
    post_json = { key:value for key,value in post_doc_obj.items()}
    post_json["_id"] = str(post_json["_id"])
    post_json["created_at"] = str(post_json["created_at"])
    if exclude_id :
        del post_json["_id"]
    return post_json

def preprocess_mongo_doc(doc):
    if isinstance(doc, dict):
        return {k: preprocess_mongo_doc(v) for k, v in doc.items()}
    elif isinstance(doc, list):
        return [preprocess_mongo_doc(item) for item in doc]
    elif isinstance(doc, ObjectId):
        return str(doc)
    return doc



def convert_str_object_id(id) :
    if not ObjectId.is_valid(id):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid post ID format."
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
