"""data_models.py

This module defines Pydantic and MongoDB data models for the application.

Key Features:
- Models for actors, conversations, messages, and wide events.
- Custom ObjectId serialization for MongoDB compatibility.
- Shared enums and type aliases.

"""

from datetime import datetime, timezone
from enum import IntEnum
from typing import Annotated, Any, List, Literal, Optional

from bson import ObjectId
from pydantic import BaseModel, ConfigDict, Field
from pydantic.json_schema import JsonSchemaValue
from pydantic_core import core_schema


class Ordering(IntEnum):
    ASCENDING = 1
    DESCENDING = -1


class ObjectIdPydanticAnnotation:
    @classmethod
    def validate_object_id(cls, v: Any, handler) -> ObjectId:
        if isinstance(v, ObjectId):
            return v

        v = handler(v)
        if ObjectId.is_valid(v):
            return ObjectId(v)

        raise ValueError("Invalid ObjectId")

    @classmethod
    def __get_pydantic_core_schema__(
        cls, source_type, handler
    ) -> core_schema.CoreSchema:
        assert source_type is ObjectId

        return core_schema.no_info_wrap_validator_function(
            cls.validate_object_id,
            core_schema.union_schema(
                [
                    core_schema.is_instance_schema(ObjectId),
                    core_schema.str_schema(),
                ]
            ),
            serialization=core_schema.to_string_ser_schema(),
        )

    @classmethod
    def __get_pydantic_json_schema__(cls, _core_schema, handler) -> JsonSchemaValue:
        return handler(core_schema.str_schema())


PyObjectId = Annotated[ObjectId, ObjectIdPydanticAnnotation]


class ToolCall(BaseModel):
    id: Optional[PyObjectId] = Field(alias="_id", default=None)


class MessageModel(BaseModel):
    type Fields = Literal["id", "conversation_id", "created_at", "author_id", "content"]
    id: Optional[PyObjectId] = Field(alias="_id", default=None)
    conversation_id: PyObjectId = Field()
    created_at: datetime = Field(default=datetime.now(timezone.utc))
    author_id: PyObjectId = Field()
    content: str = Field()
    model_config = ConfigDict(populate_by_name=True, arbitrary_types_allowed=True)


class UpdateMessageModel(BaseModel):
    conversation_id: Optional[PyObjectId] = None
    created_at: Optional[datetime] = None
    author_id: Optional[PyObjectId] = None
    content: Optional[str] = None
    model_config = ConfigDict(
        arbitrary_types_allowed=True, json_encoders={ObjectId: str}
    )


class MessageCollection(BaseModel):
    messages: List[MessageModel]


class ConversationModel(BaseModel):
    type Fields = Literal["id", "owner_id", "created_at", "last_activity_at", "topic"]
    id: Optional[PyObjectId] = Field(alias="_id", default=None)
    owner_id: PyObjectId = Field()
    created_at: datetime = Field(default=datetime.now(timezone.utc))
    last_activity_at: datetime = Field(default=datetime.now(timezone.utc))
    topic: Optional[str] = Field()
    model_config = ConfigDict(populate_by_name=True, arbitrary_types_allowed=True)


class UpdateConversationModel(BaseModel):
    owner_id: Optional[PyObjectId] = None
    created_at: Optional[datetime] = None
    last_activity_at: Optional[datetime] = None
    topic: Optional[str] = None
    model_config = ConfigDict(
        arbitrary_types_allowed=True, json_encoders={ObjectId: str}
    )


class ConversationCollection(BaseModel):
    conversations: List[ConversationModel]


class ActorModel(BaseModel):
    type Fields = Literal[
        "id",
        "created_at",
        "last_active_at",
        "name",
        "role",
        "active_conversation_id",
    ]
    id: Optional[PyObjectId] = Field(alias="_id", default=None)
    created_at: datetime = Field(default=datetime.now(timezone.utc))
    last_active_at: datetime = Field(default=datetime.now(timezone.utc))
    name: str = Field()
    role: str = Field()
    active_conversation_id: Optional[PyObjectId] = Field(default=None)
    model_config = ConfigDict(populate_by_name=True, arbitrary_types_allowed=True)


class UpdateActorModel(BaseModel):
    created_at: Optional[datetime] = None
    last_active_at: Optional[datetime] = None
    name: Optional[str] = None
    role: Optional[str] = None
    active_conversation_id: Optional[PyObjectId] = None
    model_config = ConfigDict(
        arbitrary_types_allowed=True,
        json_encoders={ObjectId: str},
        json_schema_extra={
            "example": {
                "created_at": "2026-02-02T03:01:29.371+00:00",
                "last_active_at": "2026-02-02T03:01:29.371+00:00",
                "name": "Joe",
                "role": "user",
                "active_conversation_id": "65bf6f8eff90d692f986f6b6",
            }
        },
    )


class ActorCollection(BaseModel):
    actors: List[ActorModel]


class WideEventModel(BaseModel):
    type Fields = Literal["id", "created_at", "last_active_at", "name", "role"]
    id: Optional[PyObjectId] = Field(alias="_id", default=None)
    timestamp: datetime = Field(default=datetime.now(timezone.utc))
    model_config = ConfigDict(
        populate_by_name=True, arbitrary_types_allowed=True, extra="allow"
    )


class UpdateWideEventModel(BaseModel):
    timestamp: Optional[datetime] = None
    model_config = ConfigDict(
        arbitrary_types_allowed=True,
        json_encoders={ObjectId: str},
        json_schema_extra={
            "example": {
                "timestamp": "2026-02-02T03:01:29.371+00:00",
            }
        },
        extra="allow",
    )


class WideEventCollection(BaseModel):
    actors: List[WideEventModel]


class MessageWithoutFKsModel(MessageModel):
    author_id: None = None
    conversation_id: None = None
    author: Optional[ActorModel] = None


class FullConversationModel(ConversationModel):
    owner_id: None = None
    owner: ActorModel = Field()
    messages: List[MessageWithoutFKsModel] = Field(default=[])
