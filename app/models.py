from enum import Enum
from bson import ObjectId
from datetime import datetime , timezone
from pydantic import BaseModel , Field , EmailStr

class BasePost(BaseModel) :
    title : str = Field(...,title="Title",min_length=1)
    content : str = Field(...,title="Content",min_length=10,max_length=500)
    published : bool = Field(default=True,title="Published")
    model_config = {"extra": "forbid"}

class PostDatabase(BasePost) : 
    user_id : ObjectId = Field(...,title="User_id")
    created_at : datetime = Field(default_factory=lambda: datetime.now(timezone.utc), title="Created_at")
    model_config = {"arbitrary_types_allowed":True}

class PostUpdate(BasePost) : 
    title : str | None = Field(default=None,title="Title",min_length=1)
    content : str | None = Field(default=None,title="Content",min_length=10)


class BaseUser(BaseModel) :
    username : str = Field(...,title="Username",min_length=1)
    email : EmailStr = Field(...,title="Email")
    full_name : str = Field(...,title="Full_name",min_length=3)
    disabled : bool = Field(default=False,title="Account_disabled")
    model_config = {"extra": "forbid"}

class UserIn(BaseUser) :
    password : str = Field(...,title="Password",min_length=8,max_length=128)

class UserDatabase(BaseUser) :
    hashed_password : str = Field(...,title="Hashed_password")
    created_at : datetime = Field(default_factory=lambda: datetime.now(timezone.utc), title="Created_at")
    model_config = {"extra":"ignore"}


class UserOut(UserDatabase) :
    id : str = Field(...,title="User_id")

class Token(BaseModel):
    access_token: str
    token_type: str

class TokenData(BaseModel):
    exp: datetime | None = None
    username: str | None = None
    user_id: ObjectId | None = None
    model_config = {"arbitrary_types_allowed":True}


class EmojiEnum(str, Enum):
    GRINNING = "😀"
    GRINNING_WITH_SMILE = "😁"
    SMILEY = "😊"
    LAUGHING = "😆"
    WINK = "😉"
    SAD = "😢"
    ANGRY = "😠"
    CRYING = "😭"
    KISSING = "😘"
    SURPRISED = "😮"
    CONFUSED = "😕"
    THINKING = "🤔"
    SLEEPING = "😴"
    SILLY = "😜"
    COOL = "😎"
    NERDY = "🤓"
    WORRIED = "😟"
    TIRED = "😫"
    YAWNING = "🥱"
    SWEAT = "😅"
    ANXIOUS = "😰"
    SHOCKED = "😱"
    RELIEVED = "😌"
    PARTY = "🥳"
    HUSHED = "🤫"
    SICK = "🤢"
    VOMITING = "🤮"
    DIZZY = "😵"
    HUNGRY = "🤤"
    HEART_EYES = "😍"

class ReactionInput(BaseModel):
    post_id: ObjectId
    emoji: EmojiEnum
    model_config={"extra":"forbid","arbitrary_types_allowed":True}

class Reaction(ReactionInput):
    user_id: ObjectId