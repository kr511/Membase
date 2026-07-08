"""Memory endpoints: store encrypted chunks and search them by vector."""

import logging

from fastapi import APIRouter, HTTPException, status

from app.models.schemas import (
    MemoryCreate,
    MemoryCreated,
    MemoryMatch,
    MemorySearch,
    SearchResponse,
)
from app.services import supabase_db
from app.services.supabase_db import DatabaseError

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/memories", tags=["memories"])


@router.post(
    "",
    response_model=MemoryCreated,
    status_code=status.HTTP_201_CREATED,
    summary="Store an encrypted memory",
)
async def create_memory(payload: MemoryCreate) -> MemoryCreated:
    """Persist ciphertext + embedding. The server never sees plaintext."""
    try:
        record = await supabase_db.insert_memory(payload)
    except DatabaseError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY, detail=str(exc)
        ) from exc

    return MemoryCreated(
        id=record["id"],
        user_id=record["user_id"],
        created_at=record["created_at"],
    )


@router.post(
    "/search",
    response_model=SearchResponse,
    summary="Cosine similarity search over a tenant's memories",
)
async def search_memories(payload: MemorySearch) -> SearchResponse:
    """Return the closest encrypted memories for the given query embedding."""
    try:
        rows = await supabase_db.match_memories(payload)
    except DatabaseError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY, detail=str(exc)
        ) from exc

    matches = [
        MemoryMatch(
            id=row["id"],
            encrypted_content=row["encrypted_content"],
            similarity=row["similarity"],
            created_at=row["created_at"],
        )
        for row in rows
    ]
    return SearchResponse(matches=matches, count=len(matches))
