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
├── core/security.py         # bearer auth: resolves mb_live_ keys to tenants
├── models/schemas.py        # request/response models, 384-dim validation
└── services/supabase_db.py  # async Supabase client, inserts, match_memories RPC
client_sdk/mock_client.py    # runnable E2EE proof-of-concept client
tests/test_api.py            # auth + validation contract tests (pytest)
frontend/index.html          # dashboard: signup/login + personal API key
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

All memory endpoints require your personal API key (`mb_live_…`), which is
minted automatically when you register via the web dashboard (section 7).
The tenant identity is always derived server-side from the key — requests
never contain a `user_id`.

**Store an encrypted memory** (`embedding` must be exactly 384 floats):

```bash
curl -X POST http://localhost:8000/api/v1/memories \
  -H "Authorization: Bearer mb_live_YOUR_KEY" \
  -H "Content-Type: application/json" \
  -d "{
    \"encrypted_content\": \"BASE64_AES_GCM_CIPHERTEXT\",
    \"embedding\": [$(python3 -c 'print(",".join(["0.01"]*384))')]
  }"
```

**Search by similarity:**

```bash
curl -X POST http://localhost:8000/api/v1/memories/search \
  -H "Authorization: Bearer mb_live_YOUR_KEY" \
  -H "Content-Type: application/json" \
  -d "{
    \"query_embedding\": [$(python3 -c 'print(",".join(["0.01"]*384))')],
    \"limit\": 5,
    \"threshold\": 0.3
  }"
```

Requests without a valid key are rejected with `401`. The response contains
only `encrypted_content` and similarity scores — the server cannot decrypt
anything it returns.

**Run the test suite:**

```bash
pip install -r requirements-dev.txt
pytest
```

## 6. End-to-end proof: the mock client

With the API running and your key from the dashboard, execute:

```bash
MEMBASE_API_KEY=mb_live_YOUR_KEY python client_sdk/mock_client.py
```

It encrypts a sample text locally with AES-256-GCM, generates a simulated
384-dim embedding, stores it via the API, runs a search, and decrypts the
result locally — printing at each step what the cloud sees (ciphertext)
versus what only the client can see (plaintext).

## 7. Web dashboard (signup & API key)

`frontend/index.html` is a self-contained dashboard (Tailwind, Lucide and
supabase-js via CDN — no build step). Users register / log in with
Supabase Auth; a database trigger (`supabase/migrations/api_keys.sql`)
automatically mints a personal `mb_live_…` API key on signup, which the
dashboard shows masked with reveal/copy controls.

Open the file directly in a browser, or serve it locally:

```bash
python3 -m http.server 3000 --directory frontend
```

The Supabase URL and the **public** anon/publishable key are configured at
the top of the inline script — Row Level Security ensures users can only
ever read their own key. Never put the service_role key in the frontend.

### Deploy to GitHub Pages

`.github/workflows/deploy-pages.yml` publishes `frontend/` automatically on
every push. One-time setup:

1. **GitHub:** repo **Settings → Pages → Source: "GitHub Actions"**
   (the repo must be public, or Pages requires a paid plan).
   The dashboard then lives at `https://<owner>.github.io/<repo>/`.
2. **Supabase:** Dashboard → **Authentication → URL Configuration**:
   - set **Site URL** to the Pages URL, and
   - add it to **Redirect URLs** (plus `http://localhost:3000` for local dev).

Without step 2 the signup confirmation e-mail would redirect users to
`localhost` instead of the live page. The page passes `emailRedirectTo`
on signup, so after clicking the confirmation link users land back on the
dashboard already logged in (supabase-js picks up the session from the URL).

## Security model

- **Zero knowledge:** plaintext and encryption keys never leave the client.
  The API validates shape (384 dims, non-empty ciphertext) but cannot read content.
- **API-key authentication:** every memory endpoint requires
  `Authorization: Bearer mb_live_…`. Keys are minted per user by a database
  trigger at signup and resolved server-side to the tenant identity —
  clients can never choose or spoof a `user_id`.
- **Tenant isolation:** every query is filtered by the key owner's
  `user_id` inside the `match_memories` SQL function.
- **Locked-down database:** RLS is enabled on all tables. `memories` has no
  policies (backend-only via service role); `user_api_keys` is readable only
  by its owner; the signup trigger function is not callable via REST.
- **Key handling:** the Supabase service role key lives exclusively in the
  server's environment (`.env` is git-ignored).
- Metadata (embedding vectors, timestamps, sizes) is visible to the backend
  by design — that is what makes similarity search possible.
