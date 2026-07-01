from datetime import datetime
from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey, JSON
from app.core.database import Base


class StudentProfile(Base):
    __tablename__ = "student_profiles"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    user_id = Column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    knowledge_points = Column(JSON, default=dict, nullable=False)
    overall_difficulty = Column(Float, default=0.5, nullable=False)
    learning_style = Column(String(64), default="adaptive", nullable=False)
    session_count = Column(Integer, default=0, nullable=False)
    accuracy = Column(Float, default=0.0, nullable=False)
    last_active = Column(DateTime, default=datetime.utcnow, nullable=False)
