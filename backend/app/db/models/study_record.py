from datetime import datetime

from sqlalchemy import Column, DateTime, ForeignKey, Index, Integer, Date

from app.core.database import Base


class StudyRecord(Base):
    __tablename__ = "study_records"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    user_id = Column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    node_id = Column(Integer, nullable=True)
    duration_seconds = Column(Integer, nullable=False)
    study_date = Column(Date, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    __table_args__ = (Index("ix_study_records_user_date", "user_id", "study_date"),)
