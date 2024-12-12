from pydantic import BaseModel , Field
from datetime import datetime , timezone

class BasePost(BaseModel) :
    title : str = Field(...,title="Title",min_length=1)
    content : str = Field(...,title="Content",min_length=10)
    published : bool = Field(default=True,title="Published")
    model_config = {"extra": "forbid"}


class PostDatabase(BasePost) : 
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc), title="Created_at")


class PostUpdate(BasePost) : 
    title : str | None = Field(default=None,title="Title",min_length=1)
    content : str | None = Field(default=None,title="Content",min_length=10)
