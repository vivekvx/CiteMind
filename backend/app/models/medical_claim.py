from __future__ import annotations

from datetime import datetime
from typing import Optional

from sqlalchemy import DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from backend.app.models.base import Base


class MedicalClaim(Base):
    __tablename__ = "medical_claims"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    document_id: Mapped[int] = mapped_column(
        ForeignKey("documents.id", ondelete="CASCADE"), nullable=False, index=True
    )
    chunk_index: Mapped[int] = mapped_column(Integer, nullable=False)
    drug: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    condition: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    outcome: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    direction: Mapped[str] = mapped_column(String(20), nullable=False)
    population: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    study_type: Mapped[str] = mapped_column(String(50), nullable=False, default="unknown")
    sample_size: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    effect_size: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    confidence: Mapped[float] = mapped_column(Float, nullable=False, default=0.5)
    raw_text: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, nullable=False
    )
