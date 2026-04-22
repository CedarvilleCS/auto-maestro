"""transfer_models.py

This module defines Pydantic models for API request and response transfer.

Key Features:
- Request models for actor and conversation CRUD operations.
- Chat and MCP execution request models.
- Paginated response models.

"""

from datetime import datetime
from typing import Annotated, List, Optional

from pydantic import BaseModel, Field, StringConstraints

from backend.data_models import (
    ActorModel,
    ConversationModel,
    MessageModel,
    Ordering,
    PyObjectId,
)

type NonEmptyString = Annotated[
    str, StringConstraints(min_length=1, strip_whitespace=True)
]


class FilterParams(BaseModel):
    limit: int = Field(100, gt=0, le=100)
    page: int = Field(0, ge=0)
    order_in: Ordering = Ordering.ASCENDING


class ReadActorsRequest(FilterParams):
    order_by: ActorModel.Fields = Field("created_at")
    created_at: Optional[datetime] = None
    last_active_at: Optional[datetime] = None
    name: Optional[str] = None
    role: Optional[str] = None


class ReadActorsResponse(BaseModel):
    actors: List[ActorModel]


class CreateActorRequest(BaseModel):
    name: NonEmptyString
    role: NonEmptyString


class ReadConversationsRequest(FilterParams):
    order_by: ConversationModel.Fields = Field("created_at")
    id: Optional[PyObjectId] = Field(alias="_id", default=None)
    owner_id: Optional[PyObjectId] = None
    created_at: Optional[datetime] = None
    last_activity_at: Optional[datetime] = None
    topic: Optional[str] = None


class ReadConversationsResponse(BaseModel):
    conversations: List[ConversationModel]


class CreateConversationRequest(BaseModel):
    owner_id: PyObjectId
    topic: Optional[str] = None


class ChatRequest(BaseModel):
    actor_id: Optional[PyObjectId] = Field(
        default=None, description="MongoDB document ObjectID"
    )
    query: NonEmptyString


class ConversationsResumeRequest(BaseModel):
    actor_name: NonEmptyString


class ConversationsResumeResponse(BaseModel):
    id: Optional[PyObjectId] = Field(
        default=None, description="MongoDB document ObjectID", alias="_id"
    )
    owner_id: Optional[PyObjectId] = Field(
        default=None, description="MongoDB document ObjectID"
    )
    created_at: datetime
    last_activity_at: datetime
    topic: Optional[str]
    messages: List[MessageModel] = Field(default=[])


class McpExecuteRequest(BaseModel):
    container: str
    command: List[str]
