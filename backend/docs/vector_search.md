# Embedding / vector search architecture note

## Why sqlite-vec instead of FAISS / Chroma

- **Scale:** the corpus is 48 candidates. A dedicated search server, vector index
  format, or in-memory ANN index is infrastructure we do not need.
- **One persistence layer:** candidate metadata already lives in SQLite. Storing
  embeddings in the same file (as a `vec0` virtual table) removes a second
  datastore to keep in sync — the candidate_id primary key is the stable link
  and there is no cross-store consistency to manage.
- **No synchronization complexity:** seeding, embedding and retrieval all run
  against `backend/recruitment.db`. No re-indexing, no copying vectors between
  stores, no separate service to start.
- **Migration path:** sqlite-vec lives behind `VectorRepository` and
  `GeminiEmbeddingService`. If the corpus grows past the point where an embedded
  SQLite index is fast enough (thousands+ of candidates, high QPS), we can swap
  the repository for FAISS / a managed vector DB (e.g. for a fleet/enterprise
  search service) without touching the embedding service or retrieval interface.

## sqlite-vec design

- Vector storage: a single `vec0` virtual table `candidate_embeddings`
  (`candidate_id TEXT PRIMARY KEY`, `embedding float[N] distance_metric=cosine`).
- Candidate metadata stays in the ORM `candidates` table; nothing is duplicated
  inside the vector table.
- Dimension N is fixed at index creation time. It is resolved from the actual
  Gemini response (auto-detected on the first real embed, or pinned via
  `EMBEDDING_DIMENSION`). A mismatch with an existing index is a hard error —
  rebuild with `python -m app.db.embed_candidates --recreate-index`.
- Distance metric: **cosine distance** = `1 - cosine_similarity`. sqlite-vec
  returns distance, where **lower is more similar**. We keep that terminology
  everywhere and do not convert it into an arbitrary "match %".

## Component boundaries

```
EmbeddingService       text -> list[float]          (Gemini client only)
  candidate_document   Candidate -> deterministic text (shared source of truth)
VectorRepository       candidate_id + vector <-> etc vec0 index / KNN
retrieval              JD + top_k -> ranked candidates (composition layer)
embed_candidates       explicit, idempotent setup script (no auto-embed on start)
```