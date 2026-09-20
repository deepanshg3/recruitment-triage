from datetime import date

from sqlalchemy import Boolean, Date, Integer, JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.database import Base


class Candidate(Base):
    """A candidate record loaded from data/candidates.json."""

    __tablename__ = "candidates"

    id: Mapped[str] = mapped_column(String(50), primary_key=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    target_role: Mapped[str] = mapped_column(String(255))
    years_experience: Mapped[int] = mapped_column(Integer, default=0)
    source: Mapped[str] = mapped_column(String(255))
    skills: Mapped[list] = mapped_column(JSON, default=list)
    notes: Mapped[str] = mapped_column(Text, default="")
    applied_date: Mapped[date] = mapped_column(Date)
    is_shortlisted: Mapped[bool] = mapped_column(Boolean, default=False)