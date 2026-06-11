from __future__ import annotations

from datetime import datetime
from typing import Optional

from sqlalchemy import DateTime, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from backend.app.models.base import Base


class Contradiction(Base):
    __tablename__ = "contradictions"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    claim_a_id: Mapped[int] = mapped_column(
        ForeignKey("medical_claims.id", ondelete="CASCADE"), nullable=False, index=True
    )
    claim_b_id: Mapped[int] = mapped_column(
        ForeignKey("medical_claims.id", ondelete="CASCADE"), nullable=False, index=True
    )
    contradiction_type: Mapped[str] = mapped_column(String(20), nullable=False)
    severity: Mapped[str] = mapped_column(String(10), nullable=False)
    explanation: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    consensus: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, nullable=False
    )
