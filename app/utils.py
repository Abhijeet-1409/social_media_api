from bson import ObjectId
from fastapi import HTTPException , status

def convert_to_post_json(post_doc_obj,exclude_id=False) :
    post_json = { key:value for key,value in post_doc_obj.items()}
    post_json["_id"] = str(post_json["_id"])
    post_json["created_at"] = str(post_json["created_at"])
    if exclude_id :
        del post_json["_id"]
    return post_json


def convert_str_object_id(id) :
    if not ObjectId.is_valid(id):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid post ID format."
        )
    return  ObjectId(id) 