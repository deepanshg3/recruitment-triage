"""sqlite-vec storage and nearest-neighbour search for candidate embeddings.

Kept deliberately separate from the Gemini client (embedding_service.py):
this module only knows "candidate_id + vector -> vec0 table + KNN search".

Design
------
- A single `vec0` virtual table (`candidate_embeddings`) stores one vector per
  candidate_id (the candidate primary key is the stable link). The full
  candidate record stays in the ORM `candidates` table — nothing is duplicated.
- vec0 requires a fixed dimension declared at CREATE TABLE time, so the table
  is created lazily with the dimension observed from the real embedding model
  (auto-detected on first embed, or configured via EMBEDDING_DIMENSION).
- Metric: `distance_metric=cosine`. sqlite-vec returns DISTANCE, where lower
  is more similar (cosine distance = 1 - cosine similarity). We preserve that
  terminology everywhere; it is never relabelled as a similarity/percentage.
- vec0 rejects ON CONFLICT / OR REPLACE upserts, so an idempotent upsert is
  DELETE + INSERT within one transaction.
"""

import logging
import re
from dataclasses import dataclass

import sqlite_vec
from sqlalchemy import text
from sqlalchemy.engine import Engine

from app.services.errors import VectorDimensionMismatchError, VectorIndexError

logger = logging.getLogger(__name__)

INDEX_NAME = "candidate_embeddings"
_INDEX_DDL_TEMPLATE = (
    "CREATE VIRTUAL TABLE IF NOT EXISTS {name} USING vec0("
    "candidate_id TEXT PRIMARY KEY, "
    "embedding float[{dim}] distance_metric=cosine)"
)
_DIM_PATTERN = re.compile(r"float\[(\d+)\]")


@dataclass
class SearchResult:
    candidate_id: str
    distance: float


def serialize_vector(vector: list[float]) -> bytes:
    """Encode a Python list of floats into sqlite-vec's float32 blob format."""
    return sqlite_vec.serialize_float32(vector)


class VectorRepository:
    """CRUD + KNN over the vec0 candidate_embeddings table for one engine."""

    def __init__(self, engine: Engine) -> None:
        self._engine = engine

    # -- schema -------------------------------------------------------------

    def has_index(self) -> bool:
        with self._engine.connect() as conn:
            row = conn.execute(
                text("SELECT 1 FROM sqlite_master WHERE name = :n"), {"n": INDEX_NAME}
            ).first()
            return row is not None

    def index_dimension(self) -> int | None:
        """Declared dimension of the existing vec0 index, or None if absent."""
        if not self.has_index():
            return None
        with self._engine.connect() as conn:
            row = conn.execute(
                text("SELECT sql FROM sqlite_master WHERE name = :n"),
                {"n": INDEX_NAME},
            ).first()
        match = (_DIM_PATTERN.search(row[0]) if row else None)
        if match is None:
            raise VectorIndexError(
                f"Cannot determine dimension of existing index {INDEX_NAME}."
            )
        return int(match.group(1))

    def ensure_index(self, dimension: int) -> None:
        """Create the vec0 index with `dimension` if missing.

        If it already exists with a DIFFERENT declared dimension, fail clearly —
        never silently store incompatible vectors.
        """
        dimension = int(dimension)
        if dimension <= 0:
            raise VectorIndexError(
                f"Invalid embedding dimension {dimension}; must be positive."
            )
        if self.has_index():
            declared = self.index_dimension()
            if declared != dimension:
                raise VectorDimensionMismatchError(
                    f"Existing vector index {INDEX_NAME} has dimension {declared} "
                    f"but the embedding model produced dimension {dimension}. "
                    "The embedding model changed. Rebuild the index with "
                    "`python -m app.db.embed_candidates --recreate-index`."
                )
            return
        ddl = _INDEX_DDL_TEMPLATE.format(name=INDEX_NAME, dim=dimension)
        with self._engine.begin() as conn:
            conn.execute(text(ddl))
        logger.info("Created sqlite-vec index %s (dim=%d)", INDEX_NAME, dimension)

    def drop_index(self) -> None:
        with self._engine.begin() as conn:
            conn.execute(text(f"DROP TABLE IF EXISTS {INDEX_NAME}"))

    # -- writes -------------------------------------------------------------

    def save(self, candidate_id: str, vector: list[float]) -> None:
        """Upsert one embedding for a candidate. Idempotent: safe to repeat."""
        if not self.has_index():
            raise VectorIndexError(
                f"Index {INDEX_NAME} does not exist; call ensure_index() first."
            )
        blob = serialize_vector(vector)
        with self._engine.begin() as conn:
            conn.execute(
                text(f"DELETE FROM {INDEX_NAME} WHERE candidate_id = :cid"),
                {"cid": candidate_id},
            )
            try:
                conn.execute(
                    text(
                        f"INSERT INTO {INDEX_NAME}(candidate_id, embedding) "
                        "VALUES (:cid, :vec)"
                    ),
                    {"cid": candidate_id, "vec": blob},
                )
            except Exception as exc:  # e.g. wrong vector length
                message = str(exc)
                if "dimension" in message.lower() or "expected" in message.lower():
                    raise VectorDimensionMismatchError(
                        f"Failed to store embedding for {candidate_id}: "
                        f"{message.strip()}"
                    ) from exc
                raise

    def delete(self, candidate_id: str) -> None:
        with self._engine.begin() as conn:
            conn.execute(
                text(f"DELETE FROM {INDEX_NAME} WHERE candidate_id = :cid"),
                {"cid": candidate_id},
            )

    def prune(self, valid_ids: set[str]) -> None:
        """Delete embeddings whose candidate no longer exists."""
        ids = list(valid_ids)
        if not ids:
            return
        placeholders = ", ".join(f":id_{i}" for i in range(len(ids)))
        params = {f"id_{i}": cid for i, cid in enumerate(ids)}
        with self._engine.begin() as conn:
            conn.execute(
                text(
                    f"DELETE FROM {INDEX_NAME} "
                    f"WHERE candidate_id NOT IN ({placeholders})"
                ),
                params,
            )

    # -- reads --------------------------------------------------------------

    def has(self, candidate_id: str) -> bool:
        if not self.has_index():
            return False
        with self._engine.connect() as conn:
            row = conn.execute(
                text(
                    f"SELECT 1 FROM {INDEX_NAME} WHERE candidate_id = :cid"
                ),
                {"cid": candidate_id},
            ).first()
            return row is not None

    def count(self) -> int:
        if not self.has_index():
            return 0
        with self._engine.connect() as conn:
            return conn.execute(
                text(f"SELECT count(*) FROM {INDEX_NAME}")
            ).scalar_one()

    def search(self, vector: list[float], top_k: int) -> list[SearchResult]:
        """Nearest neighbours by cosine distance, ascending. Empty if none."""
        if not self.has_index():
            raise VectorIndexError(
                "No embedding index exists. Run "
                "`python -m app.db.embed_candidates` first."
            )
        blob = serialize_vector(vector)
        sql = (
            f"SELECT candidate_id, distance FROM {INDEX_NAME} "
            "WHERE embedding MATCH :q AND k = :k ORDER BY distance"
        )
        try:
            with self._engine.connect() as conn:
                rows = conn.execute(
                    text(sql), {"q": blob, "k": top_k}
                ).all()
        except Exception as exc:
            if "dimension mismatch" in str(exc).lower():
                raise VectorDimensionMismatchError(
                    f"Query vector dimension does not match index "
                    f"dimension ({self.index_dimension()})."
                ) from exc
            raise
        return [SearchResult(candidate_id=row[0], distance=float(row[1])) for row in rows]