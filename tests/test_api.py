"""API tests: authentication, validation, and tenant derivation.

The Supabase access layer is monkeypatched — these tests cover the HTTP
contract, not the database (supabase/setup_db.py covers the live DB).
"""

import os
from datetime import datetime, timezone
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

os.environ.setdefault("SUPABASE_URL", "https://test.supabase.co")
os.environ.setdefault("SUPABASE_SERVICE_KEY", "test-service-key")

from app.main import app  # noqa: E402
from app.services import supabase_db  # noqa: E402

VALID_KEY = "mb_live_0123456789abcdef0123456789abcdef"
KEY_OWNER = "11111111-2222-3333-4444-555555555555"
EMBEDDING = [0.1] * 384


@pytest.fixture()
def client(monkeypatch: pytest.MonkeyPatch) -> TestClient:
    """Test client with a fake key store and in-memory persistence."""

    async def fake_resolve_api_key(api_key: str) -> str | None:
        return KEY_OWNER if api_key == VALID_KEY else None

    async def fake_insert_memory(user_id: str, memory) -> dict:
        return {
            "id": str(uuid4()),
            "user_id": user_id,
            "created_at": datetime.now(timezone.utc).isoformat(),
        }

    async def fake_match_memories(user_id: str, search) -> list[dict]:
        assert user_id == KEY_OWNER  # tenant must come from the API key
        return [
            {
                "id": str(uuid4()),
                "encrypted_content": "Y2lwaGVydGV4dA==",
                "similarity": 0.97,
                "created_at": datetime.now(timezone.utc).isoformat(),
            }
        ]

    monkeypatch.setattr(supabase_db, "resolve_api_key", fake_resolve_api_key)
    monkeypatch.setattr(supabase_db, "insert_memory", fake_insert_memory)
    monkeypatch.setattr(supabase_db, "match_memories", fake_match_memories)
    return TestClient(app)


def auth(key: str = VALID_KEY) -> dict[str, str]:
    return {"Authorization": f"Bearer {key}"}


class TestAuthentication:
    def test_missing_key_is_rejected(self, client: TestClient) -> None:
        response = client.post(
            "/api/v1/memories",
            json={"encrypted_content": "abc", "embedding": EMBEDDING},
        )
        assert response.status_code == 401

    def test_wrong_format_is_rejected(self, client: TestClient) -> None:
        response = client.post(
            "/api/v1/memories",
            headers=auth("sk-not-a-membase-key"),
            json={"encrypted_content": "abc", "embedding": EMBEDDING},
        )
        assert response.status_code == 401

    def test_unknown_key_is_rejected(self, client: TestClient) -> None:
        response = client.post(
            "/api/v1/memories",
            headers=auth("mb_live_deadbeefdeadbeefdeadbeefdeadbeef"),
            json={"encrypted_content": "abc", "embedding": EMBEDDING},
        )
        assert response.status_code == 401
        assert response.json()["detail"] == "Invalid API key."


class TestMemories:
    def test_create_derives_tenant_from_key(self, client: TestClient) -> None:
        response = client.post(
            "/api/v1/memories",
            headers=auth(),
            json={"encrypted_content": "Y2lwaGVydGV4dA==", "embedding": EMBEDDING},
        )
        assert response.status_code == 201
        assert response.json()["user_id"] == KEY_OWNER

    def test_client_supplied_user_id_is_ignored(self, client: TestClient) -> None:
        response = client.post(
            "/api/v1/memories",
            headers=auth(),
            json={
                "user_id": "victim-user",  # must have no effect
                "encrypted_content": "Y2lwaGVydGV4dA==",
                "embedding": EMBEDDING,
            },
        )
        assert response.status_code == 201
        assert response.json()["user_id"] == KEY_OWNER

    def test_wrong_embedding_length_is_rejected(self, client: TestClient) -> None:
        response = client.post(
            "/api/v1/memories",
            headers=auth(),
            json={"encrypted_content": "abc", "embedding": [0.1, 0.2]},
        )
        assert response.status_code == 422

    def test_search_scopes_to_key_owner(self, client: TestClient) -> None:
        response = client.post(
            "/api/v1/memories/search",
            headers=auth(),
            json={"query_embedding": EMBEDDING, "limit": 3, "threshold": 0.5},
        )
        assert response.status_code == 200
        body = response.json()
        assert body["count"] == 1
        assert body["matches"][0]["similarity"] == pytest.approx(0.97)

    def test_health_needs_no_key(self, client: TestClient) -> None:
        assert client.get("/health").status_code == 200
