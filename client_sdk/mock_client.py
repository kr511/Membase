"""MemBase mock client — proof of the zero-knowledge concept.

Simulates what a real client SDK does entirely on the user's machine:

1. Encrypt the plaintext with AES-256-GCM under a key only the user holds.
2. Compute an embedding locally (simulated here with a random 384-dim vector).
3. Send ONLY ciphertext + vector to the MemBase API.
4. Decrypt search results locally.

Run it standalone:

    python client_sdk/mock_client.py

The crypto round-trip always runs. The API calls are attempted against a
locally running instance (uvicorn app.main:app) and skipped gracefully if
the server is not up.
"""

import base64
import math
import os
import random
import sys

import httpx
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

API_BASE_URL = os.environ.get("MEMBASE_API_URL", "http://localhost:8000")
EMBEDDING_DIMENSIONS = 384
NONCE_SIZE = 12  # bytes, recommended for AES-GCM


def encrypt(plaintext: str, key: bytes) -> str:
    """AES-256-GCM encrypt; returns base64(nonce || ciphertext+tag)."""
    nonce = os.urandom(NONCE_SIZE)
    ciphertext = AESGCM(key).encrypt(nonce, plaintext.encode("utf-8"), None)
    return base64.b64encode(nonce + ciphertext).decode("ascii")


def decrypt(payload_b64: str, key: bytes) -> str:
    """Inverse of encrypt(); raises if the ciphertext was tampered with."""
    raw = base64.b64decode(payload_b64)
    nonce, ciphertext = raw[:NONCE_SIZE], raw[NONCE_SIZE:]
    return AESGCM(key).decrypt(nonce, ciphertext, None).decode("utf-8")


def fake_local_embedding(dimensions: int = EMBEDDING_DIMENSIONS) -> list[float]:
    """Stand-in for a local embedding model such as all-MiniLM-L6-v2."""
    vector = [random.uniform(-1.0, 1.0) for _ in range(dimensions)]
    norm = math.sqrt(sum(v * v for v in vector)) or 1.0
    return [v / norm for v in vector]


def main() -> int:
    print("=== MemBase mock client: end-to-end encryption demo ===\n")

    # --- happens ONLY on the user's machine -------------------------------
    user_id = "demo-user-001"
    user_key = AESGCM.generate_key(bit_length=256)  # never leaves the client
    plaintext = "The user's cat is called Schrödinger and prefers tuna."

    ciphertext_b64 = encrypt(plaintext, user_key)
    embedding = fake_local_embedding()

    print(f"[local]  plaintext:            {plaintext}")
    print(f"[local]  AES-256-GCM key:      {base64.b64encode(user_key).decode()} (stays local!)")
    print(f"[cloud]  what the API sees:    {ciphertext_b64[:60]}...")
    print(f"[cloud]  embedding vector:     {EMBEDDING_DIMENSIONS} floats, e.g. {embedding[:3]}\n")

    # Sanity check: the ciphertext round-trips locally.
    assert decrypt(ciphertext_b64, user_key) == plaintext
    print("[local]  decrypt(encrypt(x)) == x  ✔  (crypto round-trip OK)\n")

    # --- talk to the API ---------------------------------------------------
    try:
        with httpx.Client(base_url=API_BASE_URL, timeout=10.0) as client:
            store = client.post(
                "/api/v1/memories",
                json={
                    "user_id": user_id,
                    "encrypted_content": ciphertext_b64,
                    "embedding": embedding,
                },
            )
            store.raise_for_status()
            print(f"[api]    POST /api/v1/memories -> {store.status_code}")
            print(f"[api]    stored as: {store.json()}\n")

            search = client.post(
                "/api/v1/memories/search",
                json={
                    "user_id": user_id,
                    "query_embedding": embedding,
                    "limit": 3,
                    "threshold": 0.3,
                },
            )
            search.raise_for_status()
            body = search.json()
            print(f"[api]    POST /api/v1/memories/search -> {search.status_code}")
            print(f"[api]    {body['count']} match(es) returned — all still encrypted:")
            for match in body["matches"]:
                print(f"[cloud]    similarity={match['similarity']:.3f} "
                      f"content={match['encrypted_content'][:40]}...")
                print(f"[local]    decrypted locally: {decrypt(match['encrypted_content'], user_key)}")
    except httpx.HTTPError as exc:
        print(f"[api]    API not reachable at {API_BASE_URL} ({exc.__class__.__name__}).")
        print("[api]    Start it with: uvicorn app.main:app --reload")
        print("[api]    The crypto demo above already proves the E2EE concept.")
        return 0

    print("\nProof complete: the backend only ever handled ciphertext + vectors.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
