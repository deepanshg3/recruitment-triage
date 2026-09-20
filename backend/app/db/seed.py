"""Seed the candidates table from data/candidates.json.

Safe to run repeatedly: existing candidates (matched by primary key id) are
skipped, so no duplicates are created and any triage flags set later
(e.g. is_shortlisted) are preserved.
"""

import json

from sqlalchemy.orm import Session

from app.core.config import settings
from app.db.database import SessionLocal, init_db
from app.models.candidate import Candidate
from app.schemas.candidate import CandidateCreate


def load_candidates() -> list[dict]:
    with open(settings.candidates_data_path, encoding="utf-8") as f:
        return json.load(f)


def seed(db: Session) -> int:
    """Insert candidates that are not already present. Returns count added."""
    records = load_candidates()
    existing_ids = {candidate_id for (candidate_id,) in db.query(Candidate.id).all()}

    added = 0
    for raw in records:
        data = CandidateCreate(**raw)
        if data.id in existing_ids:
            continue
        db.add(Candidate(**data.model_dump()))
        added += 1
    db.commit()
    return added


def main() -> None:
    init_db()
    db = SessionLocal()
    try:
        added = seed(db)
    finally:
        db.close()
    print(f"Seeding complete: {added} candidate(s) added.")


if __name__ == "__main__":
    main()