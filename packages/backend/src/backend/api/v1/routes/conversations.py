"""conversations.py

This module defines REST endpoints for managing conversations and chat.

Key Features:
- List, create, read, update, and delete conversations.
- Send chat messages and stream AI agent responses.
- Resume conversations from persisted history.

"""

from typing import Annotated, Any, Dict, cast

from backend.data_models import (
    ConversationModel,
    FullConversationModel,
    MessageModel,
    Ordering,
    UpdateConversationModel,
)
from backend.dependencies import ChatServiceDep, DbServiceDep
from backend.transfer_models import (
    ChatRequest,
    ConversationsResumeRequest,
    CreateConversationRequest,
    ReadConversationsRequest,
    ReadConversationsResponse,
)
from bson import ObjectId
from fastapi import APIRouter, HTTPException, Query
from langchain_core.messages import AIMessage, HumanMessage

router = APIRouter(
    prefix="/conversations",
)


def _to_object_id(id_value: str) -> ObjectId:
    if not ObjectId.is_valid(id_value):
        raise HTTPException(status_code=400, detail="Invalid conversation id")
    return ObjectId(id_value)


def _message_sort_key(message: dict) -> tuple[str, str]:
    created_at = message.get("created_at")
    message_id = message.get("_id") or message.get("id") or ""
    return (str(created_at or ""), str(message_id))


@router.get(
    "/",
    response_model=ReadConversationsResponse,
    response_model_by_alias=False,
)
async def read_conversations(
    req: Annotated[ReadConversationsRequest, Query()],
    db: DbServiceDep,
):
    conversations = await db.read_conversations(
        req.model_dump(
            by_alias=True,
            exclude_none=True,
            exclude={
                "limit",
                "page",
                "order_by",
                "order_in",
            },
        ),
        req.page,
        req.limit,
        req.order_by,
        req.order_in,
    )
    return {"conversations": conversations}


@router.post("", response_model=ConversationModel, response_model_by_alias=False)
async def create_conversation(req: CreateConversationRequest, db: DbServiceDep):
    conversation = await db.create_conversation(req.owner_id, req.topic)
    conversation_id = conversation.id
    if conversation_id is None:
        raise HTTPException(status_code=500, detail="Conversation creation failed")
    await db.set_actor_active_conversation(req.owner_id, conversation_id)
    return conversation


@router.get(
    "/{conversation_id}",
    response_model=FullConversationModel,
    response_model_by_alias=False,
)
async def read_conversation(conversation_id: str, db: DbServiceDep):
    results = await db.read_full_conversations(
        {"_id": _to_object_id(conversation_id)},
        limit=1,
    )
    if not results:
        raise HTTPException(status_code=404, detail="Conversation not found")

    existing = results[0]
    payload = (
        existing.model_dump(by_alias=True)
        if hasattr(existing, "model_dump")
        else dict(existing)
    )
    payload.pop("owner_id", None)
    payload.setdefault("messages", [])
    if isinstance(payload["messages"], list):
        payload["messages"] = sorted(
            payload["messages"],
            key=lambda msg: (
                _message_sort_key(msg) if isinstance(msg, dict) else ("", "")
            ),
        )
    return FullConversationModel.model_validate(payload)


@router.patch("/{conversation_id}")
async def update_conversation(
    conversation_id: str, req: UpdateConversationModel, db: DbServiceDep
):
    updates = req.model_dump(by_alias=True, exclude_none=True)
    if not updates:
        return 0

    conversation = await db.update_conversations(
        {"_id": _to_object_id(conversation_id)}, {"$set": updates}
    )
    return conversation


@router.delete("/{conversation_id}")
async def delete_conversation(conversation_id: str, db: DbServiceDep):
    conversation = await db.delete_conversations(
        {"_id": _to_object_id(conversation_id)}
    )
    return conversation


@router.post("/{conversationId}/messages", response_model=MessageModel)
async def create_message(
    conversationId: str,
    req: ChatRequest,
    chat_service: ChatServiceDep,
    db_service: DbServiceDep,
):
    conversation_id = _to_object_id(conversationId)
    conversation = await db_service.read_conversation({"_id": conversation_id})
    if not conversation:
        raise HTTPException(status_code=404, detail="Conversation not found")

    conversation_doc = cast(dict[str, Any], conversation)
    conversation_owner_id = conversation_doc.get("owner_id")
    if req.actor_id is None:
        raise HTTPException(status_code=400, detail="actor_id is required")

    actor_id = req.actor_id
    if actor_id != conversation_owner_id:
        raise HTTPException(status_code=400, detail="actor_id is required")

    await db_service.set_actor_active_conversation(actor_id, conversation_id)

    actor = await db_service.read_actor({"_id": actor_id})
    if not actor:
        raise HTTPException(status_code=404, detail="Actor not found")

    actor_doc = cast(dict[str, Any], actor)
    actor_doc_id = actor_doc.get("_id")
    if actor_doc_id is None:
        raise HTTPException(status_code=500, detail="Actor id missing")

    await db_service.create_message(conversation_id, actor_doc_id, req.query)
    message_history = await db_service.read_messages(
        {"conversation_id": conversation_id},
        limit=100,
        order_in=Ordering.ASCENDING,
    )
    messages = []
    for message in message_history:
        message_doc = cast(dict[str, Any], message)
        author_id = message_doc.get("author_id")
        content = message_doc.get("content")

        if content is None:
            continue

        actor = await db_service.read_actor({"_id": author_id})
        if not actor:
            raise HTTPException(
                status_code=404,
                detail=f"Actor {author_id} referenced by message was not found",
            )

        actor_doc = cast(dict[str, Any], actor)
        role = actor_doc.get("role")
        match role:
            case "user":
                messages.append(HumanMessage(content=content))
            case "assistant":
                messages.append(AIMessage(content=content))

    response: Dict[str, str] = chat_service.chat(messages)
    # TODO: This could be co-agents or subagents
    # assistant_name = (
    #     response.get("name") if response.get("name") is not None else "AutoMAESTRO"
    # )
    assistant_content = response.get("response", "No content")
    assistant_actor = await db_service.read_actor({"name": "AutoMAESTRO"})
    if not assistant_actor:
        raise HTTPException(status_code=500, detail="Assistant actor is not configured")

    assistant_actor_doc = cast(dict[str, Any], assistant_actor)
    assistant_actor_id = assistant_actor_doc.get("_id")
    if assistant_actor_id is None:
        raise HTTPException(status_code=500, detail="Assistant actor id missing")

    assistant_message = await db_service.create_message(
        conversation_id, assistant_actor_id, assistant_content
    )

    return assistant_message


@router.post(
    "/resume",
    response_model=FullConversationModel,
    response_model_by_alias=False,
)
async def resume_conversation(
    req: ConversationsResumeRequest,
    db_service: DbServiceDep,
):
    actors = await db_service.read_actors({"name": req.actor_name})

    if not actors:
        raise HTTPException(
            status_code=404,
            detail=f"User does not exist with name {req.actor_name}",
        )

    if len(actors) > 1:
        raise HTTPException(status_code=409, detail="Database integrity compromised")

    actor = actors[0]
    actor_doc = cast(dict[str, Any], actor)
    actor_id = actor_doc.get("_id")
    if actor_id is None:
        raise HTTPException(status_code=500, detail="Actor id missing")

    active_conversation_id = actor_doc.get("active_conversation_id")

    if active_conversation_id:
        active_conversation = await db_service.read_full_conversations(
            {
                "_id": active_conversation_id,
                "owner._id": actor_id,
            },
            limit=1,
        )
        if active_conversation:
            existing = active_conversation[0]
            payload = (
                existing.model_dump(by_alias=True)
                if hasattr(existing, "model_dump")
                else dict(existing)
            )
            payload.pop("owner_id", None)
            payload.setdefault("messages", [])
            if isinstance(payload["messages"], list):
                payload["messages"] = sorted(
                    payload["messages"],
                    key=lambda msg: (
                        _message_sort_key(msg) if isinstance(msg, dict) else ("", "")
                    ),
                )
            return FullConversationModel.model_validate(payload)

    last_conversation = await db_service.read_full_conversations(
        {"owner._id": actor_id},
        limit=1,
        order_by="last_activity_at",
        order_in=Ordering.DESCENDING,
    )

    if last_conversation:
        existing = last_conversation[0]
        payload = (
            existing.model_dump(by_alias=True)
            if hasattr(existing, "model_dump")
            else dict(existing)
        )
        payload.pop("owner_id", None)
        payload.setdefault("messages", [])
        if isinstance(payload["messages"], list):
            payload["messages"] = sorted(
                payload["messages"],
                key=lambda msg: (
                    _message_sort_key(msg) if isinstance(msg, dict) else ("", "")
                ),
            )

        existing_conversation_id = payload.get("_id") or payload.get("id")
        if existing_conversation_id:
            await db_service.set_actor_active_conversation(
                actor_id, existing_conversation_id
            )

        return FullConversationModel.model_validate(payload)

    new_conversation = await db_service.create_conversation(actor_id)
    new_conversation_id = new_conversation.id
    if new_conversation_id is None:
        raise HTTPException(status_code=500, detail="Conversation creation failed")
    await db_service.set_actor_active_conversation(actor_id, new_conversation_id)
    payload = new_conversation.model_dump(by_alias=True)
    payload.pop("owner_id", None)
    payload["owner"] = actor_doc
    payload["messages"] = []

    return FullConversationModel.model_validate(payload)
