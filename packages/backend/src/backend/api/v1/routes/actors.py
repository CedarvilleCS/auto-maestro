"""actors.py

This module defines REST endpoints for managing actor resources.

Key Features:
- List, create, read, update, and delete actors.
- Input validation and duplicate detection.
- Pagination and filtering support.

"""

from typing import Annotated

from backend.data_models import ActorModel, UpdateActorModel
from backend.dependencies import DbServiceDep
from backend.transfer_models import (
    CreateActorRequest,
    ReadActorsRequest,
    ReadActorsResponse,
)
from bson import ObjectId
from fastapi import APIRouter, HTTPException, Query
from pymongo.errors import DuplicateKeyError

router = APIRouter(prefix="/actors")


def _to_object_id(id_value: str) -> ObjectId:
    if not ObjectId.is_valid(id_value):
        raise HTTPException(status_code=400, detail="Invalid actor id")
    return ObjectId(id_value)


@router.get("", response_model=ReadActorsResponse)
async def read_actors(req: Annotated[ReadActorsRequest, Query()], db: DbServiceDep):
    actors = await db.read_actors(
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
    return {"actors": actors}


@router.post(
    "",
    response_model=ActorModel,
    responses={
        409: {
            "content": {
                "application/json": {
                    "example": {"detail": "Actor with that name already exists"}
                }
            },
            "description": "Duplicate resource",
        }
    },
)
async def create_actor(req: CreateActorRequest, db: DbServiceDep):
    try:
        actor = await db.create_actor(req.name, req.role)
    except DuplicateKeyError:
        raise HTTPException(409, detail="Actor with that name already exists")
    return actor


@router.get("/{actor_id}", response_model=ActorModel)
async def read_actor(actor_id: str, db: DbServiceDep):
    actor = await db.read_actor({"_id": _to_object_id(actor_id)})
    return actor


@router.patch("/{actor_id}")
async def update_actor(actor_id: str, req: UpdateActorModel, db: DbServiceDep):
    updates = req.model_dump(by_alias=True, exclude_none=True)
    if not updates:
        return 0

    actor = await db.update_actors({"_id": _to_object_id(actor_id)}, {"$set": updates})
    return actor


@router.delete("/{actor_id}")
async def delete_actor(actor_id: str, db: DbServiceDep):
    actor = await db.delete_actors({"_id": _to_object_id(actor_id)})
    return actor
