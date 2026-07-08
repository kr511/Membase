"""MemBase database setup & validation.

Connects to Supabase with the credentials from .env, verifies that the
schema from supabase/schema.sql has been applied, and runs an end-to-end
smoke test (insert a test vector, find it via the match_memories RPC,
clean up).

The Supabase Python client talks to PostgREST and cannot execute raw DDL,
so the schema itself must be applied once via the SQL Editor or the
Supabase CLI — this script tells you exactly how if anything is missing.

Usage (from the repository root):

    python supabase/setup_db.py
"""

import random
import sys
import uuid
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

from postgrest.exceptions import APIError  # noqa: E402
from supabase import Client, create_client  # noqa: E402

SCHEMA_FILE = Path(__file__).with_name("schema.sql")
EMBEDDING_DIMENSIONS = 384
TEST_USER_ID = "membase-setup-smoke-test"

MISSING_ENV_HELP = f"""
ERROR: Supabase credentials are not configured.

How to fix this:

  1. Copy the template:        cp .env.example .env
  2. Open your Supabase dashboard -> Settings -> API
  3. Fill in .env:
       SUPABASE_URL=https://<your-project-ref>.supabase.co
       SUPABASE_SERVICE_KEY=<your service_role key>
  4. Re-run this script:       python supabase/setup_db.py

The service_role key must stay server-side only — never commit .env
or ship this key to clients.
"""

SCHEMA_MISSING_HELP = f"""
The 'memories' table (or the match_memories function) does not exist yet.

The Supabase Python client cannot run DDL statements, so apply the schema
once using either option:

  Option A — Supabase Dashboard:
    1. Open the dashboard -> SQL Editor
    2. Paste the contents of: {SCHEMA_FILE}
    3. Run it (all statements are idempotent)

  Option B — Supabase CLI:
    supabase link --project-ref <your-project-ref>
    supabase db push

Then re-run this script to validate the setup:
    python supabase/setup_db.py
"""


def load_settings() -> "object | None":
    """Load settings from the environment/.env; print help if incomplete."""
    from pydantic import ValidationError

    from app.core.config import Settings

    try:
        return Settings()  # type: ignore[call-arg]
    except ValidationError as exc:
        missing = ", ".join(
            str(err["loc"][0]) for err in exc.errors() if err["type"] == "missing"
        )
        print(MISSING_ENV_HELP)
        if missing:
            print(f"Missing variables: {missing}")
        return None


def connect(settings: "object") -> Client | None:
    """Create a Supabase client; explain the failure if it cannot be built."""
    try:
        client = create_client(
            settings.supabase_url, settings.supabase_service_key  # type: ignore[attr-defined]
        )
        print(f"[1/4] Client created for {settings.supabase_url}")  # type: ignore[attr-defined]
        return client
    except Exception as exc:
        print(f"[1/4] Could not create Supabase client: {exc}")
        print("      Check that SUPABASE_URL looks like https://<ref>.supabase.co")
        return None


def check_schema(client: Client) -> bool:
    """Verify the memories table is reachable; print setup help if not."""
    try:
        client.table("memories").select("id").limit(1).execute()
        print("[2/4] Table 'memories' exists and is reachable.")
        return True
    except APIError as exc:
        if exc.code == "42P01":  # undefined_table
            print("[2/4] Table 'memories' not found.")
            print(SCHEMA_MISSING_HELP)
        else:
            print(f"[2/4] Unexpected database error ({exc.code}): {exc.message}")
        return False
    except Exception as exc:
        print(f"[2/4] Connection failed: {exc.__class__.__name__}: {exc}")
        print("      Check SUPABASE_URL / SUPABASE_SERVICE_KEY and your network.")
        return False


def _random_unit_vector(dimensions: int = EMBEDDING_DIMENSIONS) -> list[float]:
    vector = [random.uniform(-1.0, 1.0) for _ in range(dimensions)]
    norm = sum(v * v for v in vector) ** 0.5 or 1.0
    return [v / norm for v in vector]


def run_smoke_test(client: Client) -> bool:
    """Insert a test vector, retrieve it via the RPC, and clean up."""
    marker = f"setup-test-{uuid.uuid4()}"
    embedding = _random_unit_vector()
    row_id: str | None = None

    try:
        # Insert.
        response = (
            client.table("memories")
            .insert(
                {
                    "user_id": TEST_USER_ID,
                    "encrypted_content": marker,
                    "embedding": embedding,
                }
            )
            .execute()
        )
        row_id = response.data[0]["id"]
        print(f"[3/4] Inserted test vector (id={row_id}).")

        # Query it back via the RPC — searching with the same vector must
        # return the row with similarity ~1.0.
        matches = client.rpc(
            "match_memories",
            {
                "query_embedding": embedding,
                "match_threshold": 0.9,
                "match_count": 5,
                "owner_id": TEST_USER_ID,
            },
        ).execute()
        found = [m for m in (matches.data or []) if m["encrypted_content"] == marker]
        if not found:
            print("[4/4] FAILED: test vector not returned by match_memories().")
            print("      Is the match_memories function from schema.sql installed?")
            return False
        print(
            f"[4/4] match_memories() returned the test vector "
            f"(similarity={found[0]['similarity']:.4f})."
        )
        return True
    except APIError as exc:
        if exc.code == "42883":  # undefined_function
            print("[4/4] FAILED: RPC function match_memories() does not exist.")
            print(SCHEMA_MISSING_HELP)
        else:
            print(f"[4/4] FAILED with database error ({exc.code}): {exc.message}")
        return False
    finally:
        # Always remove the test row.
        if row_id is not None:
            try:
                client.table("memories").delete().eq("id", row_id).execute()
                print(f"      Cleaned up test row {row_id}.")
            except Exception as exc:
                print(f"      WARNING: could not delete test row {row_id}: {exc}")


def main() -> int:
    print("=== MemBase Supabase setup & validation ===\n")

    settings = load_settings()
    if settings is None:
        return 1

    client = connect(settings)
    if client is None:
        return 1

    if not check_schema(client):
        return 1

    if not run_smoke_test(client):
        return 1

    print("\nSuccess: database schema is in place and fully functional.")
    print("Start the API with: uvicorn app.main:app --reload")
    return 0


if __name__ == "__main__":
    sys.exit(main())
