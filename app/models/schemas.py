"""Pydantic v2 request/response models for the memory API.

The API is zero-knowledge by design: it only ever accepts and returns the
AES-GCM ciphertext (`encrypted_content`) plus the embedding vector that the
client computed locally. Plaintext never appears in any schema.
"""

from datetime import datetime
from typing import Annotated
from uuid import UUID

from pydantic import BaseModel, Field

EMBEDDING_DIMENSIONS = 384

Embedding = Annotated[
    list[float],
    Field(
        min_length=EMBEDDING_DIMENSIONS,
        max_length=EMBEDDING_DIMENSIONS,
        description=f"Client-side embedding, exactly {EMBEDDING_DIMENSIONS} dimensions "
        "(e.g. all-MiniLM-L6-v2).",
    ),
]


class MemoryCreate(BaseModel):
    """Payload to store one encrypted memory chunk.

    The tenant is derived server-side from the API key — clients cannot
    choose a user_id.
    """

    encrypted_content: str = Field(
        ...,
        min_length=1,
        description="Base64-encoded AES-GCM ciphertext (nonce || ciphertext), "
        "encrypted client-side. The backend cannot decrypt this.",
    )
    embedding: Embedding


class MemorySearch(BaseModel):
    """Payload for a cosine similarity search over the caller's memories."""

    query_embedding: Embedding
    limit: int = Field(default=5, ge=1, le=100, description="Maximum number of matches.")
    threshold: float = Field(
        default=0.3, ge=0.0, le=1.0, description="Minimum cosine similarity."
    )


class MemoryCreated(BaseModel):
    """Confirmation returned after storing a memory."""

    id: UUID
    user_id: str
    created_at: datetime


class MemoryMatch(BaseModel):
    """One search hit — still encrypted; only the client can decrypt it."""

    id: UUID
    encrypted_content: str
    similarity: float
    created_at: datetime


class SearchResponse(BaseModel):
    """Result set of a similarity search."""

    matches: list[MemoryMatch]
    count: int
