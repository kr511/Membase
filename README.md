# MemBase — Zero-Knowledge LLM Memory as a Service

Unlimited long-term memory for local LLMs (Ollama, LM Studio, …) with true
**end-to-end encryption**: the backend never sees plaintext. Clients encrypt
content with AES-256-GCM and compute embeddings locally; the cloud only ever
stores **ciphertext + vectors** and answers similarity searches over them.

```
┌────────────── Client (user's machine) ──────────────┐   ┌───── MemBase Cloud ─────┐
│                                                     │   │                         │
│  plaintext ──► local embedding model (384-dim)  ────┼──►│  vector(384)            │
│      │                                              │   │        │                │
│      └──────► AES-256-GCM (user key, stays local) ──┼──►│  base64 ciphertext      │
│                                                     │   │        │                │
│  decrypt search results locally ◄───────────────────┼───│  Supabase + pgvector    │
└─────────────────────────────────────────────────────┘   └─────────────────────────┘
```

**Stack:** Python 3.11+ · FastAPI (async, Pydantic v2) · Supabase (PostgreSQL + pgvector)

## Project layout

```
app/
├── main.py                  # FastAPI app factory, middleware, /health
├── api/v1/memory.py         # POST /api/v1/memories and /api/v1/memories/search
├── core/config.py           # pydantic-settings (SUPABASE_URL, SUPABASE_SERVICE_KEY)
├── models/schemas.py        # request/response models, 384-dim validation
└── services/supabase_db.py  # async Supabase client, inserts, match_memories RPC
client_sdk/mock_client.py    # runnable E2EE proof-of-concept client
supabase/schema.sql          # idempotent schema for the Supabase SQL Editor
supabase/setup_db.py         # connection check + insert/search smoke test
supabase/migrations/         # versioned SQL migration (same schema)
```

## 1. Setup

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## 2. Configure `.env`

```bash
cp .env.example .env
```

Then fill in the values from your Supabase dashboard (**Settings → API**):

| Variable | Value |
|---|---|
| `SUPABASE_URL` | Project URL, e.g. `https://abcdefgh.supabase.co` |
| `SUPABASE_SERVICE_KEY` | **Service role** key (server-side only — never expose it to clients) |

## 3. Apply the database migration

The schema lives in `supabase/migrations/20260708000000_init_vector_memory.sql`.
Apply it in one of two ways:

**Option A — Supabase Dashboard:** open **SQL Editor**, paste the file's
contents, and run it.

**Option B — Supabase CLI:**

```bash
supabase link --project-ref <your-project-ref>
supabase db push
```

Both files (`supabase/schema.sql` and the migration) are idempotent and
enable the `vector` extension, create the `memories` table (with an HNSW
cosine index), and install the `match_memories()` RPC function.

**Validate the setup:** after applying the schema, run

```bash
python supabase/setup_db.py
```

It checks your `.env` credentials, verifies the schema is reachable, inserts
a test vector, retrieves it via the `match_memories` RPC, and cleans up —
with step-by-step guidance if anything is missing.

## 4. Run the API

```bash
uvicorn app.main:app --reload
```

Interactive docs: <http://localhost:8000/docs> · Health check: `GET /health`

## 5. Test the endpoints

**Store an encrypted memory** (`embedding` must be exactly 384 floats):

```bash
curl -X POST http://localhost:8000/api/v1/memories \
  -H "Content-Type: application/json" \
  -d "{
    \"user_id\": \"demo-user-001\",
    \"encrypted_content\": \"BASE64_AES_GCM_CIPHERTEXT\",
    \"embedding\": [$(python3 -c 'print(",".join(["0.01"]*384))')]
  }"
```

**Search by similarity:**

```bash
curl -X POST http://localhost:8000/api/v1/memories/search \
  -H "Content-Type: application/json" \
  -d "{
    \"user_id\": \"demo-user-001\",
    \"query_embedding\": [$(python3 -c 'print(",".join(["0.01"]*384))')],
    \"limit\": 5,
    \"threshold\": 0.3
  }"
```

The response contains only `encrypted_content` and similarity scores — the
server cannot decrypt anything it returns.

## 6. End-to-end proof: the mock client

With the API running, execute:

```bash
python client_sdk/mock_client.py
```

It encrypts a sample text locally with AES-256-GCM, generates a simulated
384-dim embedding, stores it via the API, runs a search, and decrypts the
result locally — printing at each step what the cloud sees (ciphertext)
versus what only the client can see (plaintext).

## Security model

- **Zero knowledge:** plaintext and encryption keys never leave the client.
  The API validates shape (384 dims, non-empty ciphertext) but cannot read content.
- **Tenant isolation:** every query is filtered by `user_id` inside the
  `match_memories` SQL function.
- **Key handling:** the Supabase service role key lives exclusively in the
  server's environment (`.env` is git-ignored).
- Metadata (embedding vectors, timestamps, sizes) is visible to the backend
  by design — that is what makes similarity search possible.
