from datetime import datetime, date
from sqlalchemy import Column, Integer, String, Float, Date, DateTime, ForeignKey, Time
from app.core.database import Base


class LearningRecord(Base):
    """学习记录表 - 对应 CSV 数据格式"""
    __tablename__ = "learning_records"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    record_id = Column(String(50), unique=True, nullable=False, comment="原始记录ID")
    user_id = Column(String(20), nullable=False, comment="学生编号")
    course = Column(String(100), nullable=False, comment="课程名称")
    chapter = Column(String(100), nullable=False, comment="章节")
    score = Column(Integer, nullable=False, comment="得分")
    correct_rate = Column(Float, nullable=False, comment="正确率")
    problems_done = Column(Integer, nullable=False, comment="做题数")
    duration_minutes = Column(Integer, nullable=False, comment="学习时长(分钟)")
    study_date = Column(Date, nullable=False, comment="学习日期")
    time_slot = Column(String(20), nullable=False, comment="时间段")
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
