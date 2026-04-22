"""database.py

This module handles all MongoDB database operations.

Key Features:
- CRUD operations for actors, conversations, and messages.
- Async MongoDB client using PyMongo.
- Wide-event logging support.

"""

from datetime import datetime, timezone
from typing import Any, Dict, List, Mapping, Optional

import pymongo
from bson import ObjectId
from pymongo.asynchronous.collection import AsyncCollection

from backend.config import settings
from backend.data_models import (
    ActorModel,
    ConversationModel,
    FullConversationModel,
    MessageModel,
    Ordering,
    PyObjectId,
    WideEventModel,
)


class DatabaseService:
    def __init__(self):
        self.client = pymongo.AsyncMongoClient(settings.get_database_url())

    async def shutdown(self):
        await self.client.close()

    def get_connection(self) -> pymongo.AsyncMongoClient:
        return self.client

    def get_database(self):
        return self.client.get_database(settings.database_name)

    def get_actors(self) -> AsyncCollection[ActorModel]:
        return self.get_database().get_collection("actors")

    def get_conversations(self) -> AsyncCollection[ConversationModel]:
        return self.get_database().get_collection("conversations")

    def get_messages(self) -> AsyncCollection[MessageModel]:
        return self.get_database().get_collection("messages")

    def get_wide_events(self) -> AsyncCollection[MessageModel]:
        return self.get_database().get_collection("wide_events")

    def get_full_conversations_view(self) -> AsyncCollection[FullConversationModel]:
        return self.get_database().get_collection(
            "conversations_with_messages_and_owner"
        )

    async def create_conversation(
        self, owner_id: PyObjectId, topic: Optional[str] = None
    ) -> ConversationModel:
        conversations = self.get_conversations()

        new_conversation = ConversationModel(
            owner_id=owner_id,
            topic=topic,
        )

        document = new_conversation.model_dump(by_alias=True, exclude={"id"})
        document["owner_id"] = ObjectId(document["owner_id"])

        result = await conversations.insert_one(document)
        new_conversation.id = str(result.inserted_id)

        return new_conversation

    async def read_conversations(
        self,
        query: Mapping[str, Any],
        page: int = 0,
        limit: int = 10,
        order_by: ConversationModel.Fields = "created_at",
        order_in: Ordering = Ordering.ASCENDING,
    ) -> List[ConversationModel]:
        conversations = self.get_conversations()
        return await conversations.find(
            query,
            skip=page * limit,
            limit=limit,
            sort=[(order_by, order_in.value)],
        ).to_list()

    async def read_conversation(
        self,
        query: Mapping[str, Any],
        page: int = 0,
        limit: int = 10,
        order_by: ConversationModel.Fields = "created_at",
        order_in: Ordering = Ordering.ASCENDING,
    ) -> Optional[ConversationModel]:
        conversations = self.get_conversations()
        return await conversations.find_one(
            query,
            skip=page * limit,
            sort=[(order_by, order_in.value)],
        )

    async def update_conversations(
        self,
        filter: Mapping[str, Any],
        update: Mapping[str, Any],
    ) -> int:
        conversations = self.get_conversations()
        return (await conversations.update_many(filter, update)).modified_count

    async def delete_conversations(self, filter: Mapping[str, Any]) -> int:
        conversations = self.get_conversations()
        return (await conversations.delete_many(filter)).deleted_count

    async def create_actor(self, name: str, role: str) -> ActorModel:
        actors = self.get_actors()

        new_actor = ActorModel(name=name, role=role).model_dump(
            by_alias=True, exclude={"id"}
        )
        result = await actors.insert_one(new_actor)
        new_actor["_id"] = result.inserted_id

        return ActorModel.model_validate(new_actor)

    async def read_actors(
        self,
        query: Dict[str, Any],
        page: int = 0,
        limit: int = 10,
        order_by: ActorModel.Fields = "created_at",
        order_in: Ordering = Ordering.ASCENDING,
    ) -> List[ActorModel]:
        actors = self.get_actors()
        return await actors.find(
            query,
            skip=page * limit,
            limit=limit,
            sort=[(order_by, order_in.value)],
        ).to_list()

    async def read_actor(
        self,
        query: Dict[str, Any],
        page: int = 0,
        limit: int = 10,
        order_by: ActorModel.Fields = "created_at",
        order_in: Ordering = Ordering.ASCENDING,
    ) -> Optional[ActorModel]:
        actors = self.get_actors()
        return await actors.find_one(
            query,
            skip=page * limit,
            sort=[(order_by, order_in.value)],
        )

    async def update_actors(
        self,
        filter: Mapping[str, Any],
        update: Mapping[str, Any],
    ) -> int:
        actors = self.get_actors()
        return (await actors.update_many(filter, update)).modified_count

    async def delete_actors(self, filter: Mapping[str, Any]) -> int:
        actors = self.get_actors()
        return (await actors.delete_many(filter)).deleted_count

    async def set_actor_active_conversation(
        self, actor_id: PyObjectId, conversation_id: PyObjectId
    ) -> int:
        actors = self.get_actors()
        return (
            await actors.update_one(
                {"_id": ObjectId(actor_id)},
                {
                    "$set": {
                        "active_conversation_id": ObjectId(conversation_id),
                        "last_active_at": datetime.now(timezone.utc),
                    }
                },
            )
        ).modified_count

    async def create_message(
        self, conversation_id: PyObjectId, author_id: PyObjectId, content: str
    ) -> MessageModel:
        messages = self.get_messages()

        new_message = MessageModel(
            conversation_id=conversation_id, author_id=author_id, content=content
        )

        mongo_document = new_message.model_dump(by_alias=True, exclude={"id"})
        mongo_document["conversation_id"] = ObjectId(mongo_document["conversation_id"])
        mongo_document["author_id"] = ObjectId(mongo_document["author_id"])

        result = await messages.insert_one(mongo_document)
        await self.update_conversations(
            {"_id": conversation_id},
            {"$set": {"last_activity_at": datetime.now(timezone.utc)}},
        )
        new_message.id = str(result.inserted_id)

        return new_message

    async def read_messages(
        self,
        query: Dict[str, Any],
        page: int = 0,
        limit: int = 10,
        order_by: MessageModel.Fields = "created_at",
        order_in: Ordering = Ordering.ASCENDING,
    ) -> List[MessageModel]:
        messages = self.get_messages()
        return await messages.find(
            query,
            skip=page * limit,
            limit=limit,
            sort=[(order_by, order_in.value)],
        ).to_list()

    async def update_messages(
        self,
        filter: Mapping[str, Any],
        update: Mapping[str, Any],
    ) -> int:
        messages = self.get_messages()
        return (await messages.update_many(filter, update)).modified_count

    async def delete_messages(self, filter: Mapping[str, Any]) -> int:
        messages = self.get_messages()
        return (await messages.delete_many(filter)).deleted_count

    async def create_wide_event(
        self, wide_event: Dict[str, Any], **kwargs
    ) -> Optional[WideEventModel]:
        wide_events = self.get_wide_events()

        new_wide_event = WideEventModel(**wide_event).model_dump(
            by_alias=True, exclude={"id"}
        )
        result = await wide_events.insert_one(new_wide_event)
        new_wide_event["_id"] = result.inserted_id

        return WideEventModel.model_validate(new_wide_event)

    async def read_full_conversations(
        self,
        query: Dict[str, Any],
        page: int = 0,
        limit: int = 10,
        order_by: ConversationModel.Fields = "created_at",
        order_in: Ordering = Ordering.ASCENDING,
    ) -> List[FullConversationModel]:
        conversations = self.get_full_conversations_view()
        return await conversations.find(
            query,
            skip=page * limit,
            limit=limit,
            sort=[(order_by, order_in.value)],
        ).to_list()
