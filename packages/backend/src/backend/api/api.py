"""api.py

This module defines the top-level API router for the backend.

Key Features:
- Mounts versioned sub-routers (v1) under the /api prefix.

"""

from fastapi import APIRouter

from .v1 import v1

router = APIRouter(prefix="/api")

router.include_router(v1.router)
