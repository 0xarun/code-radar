from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Index, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class Finding(Base):
    __tablename__ = "findings"
    __table_args__ = (Index("ix_findings_job_id", "job_id"), Index("ix_findings_hash", "hash", unique=True))

    id: Mapped[int] = mapped_column(primary_key=True)
    job_id: Mapped[int] = mapped_column(ForeignKey("jobs.id", ondelete="CASCADE"), nullable=False)
    file_path: Mapped[str] = mapped_column(String(1024), nullable=False)
    rule_id: Mapped[str] = mapped_column(String(255), nullable=False)
    severity: Mapped[str] = mapped_column(String(64), nullable=False)
    code_snippet: Mapped[str] = mapped_column(Text, nullable=False)
    hash: Mapped[str] = mapped_column(String(128), nullable=False, unique=True)
    ai_analysis: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)

    job = relationship("Job", back_populates="findings")
