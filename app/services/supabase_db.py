"""Async Supabase access layer: inserts and the match_memories RPC."""

import logging
from typing import Any

from postgrest.exceptions import APIError
from supabase import AsyncClient, acreate_client

from app.core.config import get_settings
from app.models.schemas import MemoryCreate, MemorySearch

logger = logging.getLogger(__name__)

_client: AsyncClient | None = None


class DatabaseError(Exception):
    """Raised when a Supabase operation fails; safe to map to an HTTP 502."""


async def get_client() -> AsyncClient:
    """Return the shared async Supabase client, creating it on first use."""
    global _client
    if _client is None:
        settings = get_settings()
        _client = await acreate_client(
            settings.supabase_url, settings.supabase_service_key
        )
    return _client


async def close_client() -> None:
    """Drop the shared client (used on application shutdown)."""
    global _client
    _client = None


async def resolve_api_key(api_key: str) -> str | None:
    """Return the user_id owning the given API key, or None if unknown."""
    client = await get_client()
    try:
        response = await (
            client.table("user_api_keys")
            .select("user_id")
            .eq("api_key", api_key)
            .limit(1)
            .execute()
        )
    except APIError as exc:
        logger.error("Supabase API key lookup failed: %s", exc.message)
        raise DatabaseError("API key verification failed.") from exc
    except Exception as exc:  # network errors, timeouts, DNS failures
        logger.exception("Unexpected error during API key lookup")
        raise DatabaseError("API key verification failed.") from exc

    if response.data:
        return str(response.data[0]["user_id"])
    return None


async def insert_memory(user_id: str, memory: MemoryCreate) -> dict[str, Any]:
    """Persist one encrypted memory row and return the stored record."""
    client = await get_client()
    try:
        response = await (
            client.table("memories")
            .insert(
                {
                    "user_id": user_id,
                    "encrypted_content": memory.encrypted_content,
                    "embedding": memory.embedding,
                }
            )
            .execute()
        )
    except APIError as exc:
        logger.error("Supabase insert failed: %s", exc.message)
        raise DatabaseError("Failed to store memory.") from exc
    except Exception as exc:  # network errors, timeouts, DNS failures
        logger.exception("Unexpected error while storing memory")
        raise DatabaseError("Failed to store memory.") from exc

    if not response.data:
        raise DatabaseError("Insert returned no data.")
    return response.data[0]


async def match_memories(user_id: str, search: MemorySearch) -> list[dict[str, Any]]:
    """Run the match_memories RPC for one tenant and return the raw rows."""
    client = await get_client()
    try:
        response = await client.rpc(
            "match_memories",
            {
                "query_embedding": search.query_embedding,
                "match_threshold": search.threshold,
                "match_count": search.limit,
                "owner_id": user_id,
            },
        ).execute()
    except APIError as exc:
        logger.error("Supabase RPC match_memories failed: %s", exc.message)
        raise DatabaseError("Similarity search failed.") from exc
    except Exception as exc:  # network errors, timeouts, DNS failures
        logger.exception("Unexpected error during similarity search")
        raise DatabaseError("Similarity search failed.") from exc

    return response.data or []
