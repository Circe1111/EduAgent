from datetime import datetime
from sqlalchemy import Column, Integer, String, Float, DateTime, Text
from app.core.database import Base


class KnowledgeChunk(Base):
    __tablename__ = "knowledge_chunks"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    chunk_id = Column(String(255), unique=True, nullable=False, index=True)
    source = Column(String(255), nullable=False)
    chapter = Column(String(255), nullable=False)
    knowledge_point = Column(String(255), nullable=False, index=True)
    difficulty = Column(Float, default=0.5, nullable=False)
    content = Column(Text, nullable=False)
    content_hash = Column(String(64), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
