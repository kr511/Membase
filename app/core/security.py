"""API-key authentication: resolve mb_live_ keys to tenant user ids.

Clients obtain their key via the dashboard (auto-minted on signup) and send
it as `Authorization: Bearer mb_live_...`. The tenant identity is always
derived server-side from the key — never trusted from the request body.
"""

import logging

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.services import supabase_db
from app.services.supabase_db import DatabaseError

logger = logging.getLogger(__name__)

API_KEY_PREFIX = "mb_"

_bearer_scheme = HTTPBearer(
    auto_error=False,
    description="Your personal MemBase API key (mb_live_...), "
    "available in the dashboard.",
)


async def get_current_user_id(
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer_scheme),
) -> str:
    """Validate the bearer API key and return the owning user's id."""
    if credentials is None or not credentials.credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing API key. Send 'Authorization: Bearer mb_live_...'.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    api_key = credentials.credentials
    if not api_key.startswith(API_KEY_PREFIX):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid API key format.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    try:
        user_id = await supabase_db.resolve_api_key(api_key)
    except DatabaseError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY, detail=str(exc)
        ) from exc

    if user_id is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid API key.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return user_id
