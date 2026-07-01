from datetime import datetime
from sqlalchemy import Column, Integer, String, Text, DateTime
from app.core.database import Base


class PromptTemplate(Base):
    """Prompt 模板表"""
    __tablename__ = "prompt_templates"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    code = Column(String(20), unique=True, nullable=False, comment="模板编号 P001-P030")
    title = Column(String(100), nullable=False, comment="模板标题")
    role = Column(String(200), nullable=False, comment="角色设定")
    task = Column(String(200), nullable=False, comment="任务描述")
    template = Column(Text, nullable=False, comment="模板内容（含变量占位符）")
    variables = Column(String(200), nullable=False, comment="变量列表，逗号分隔")
    scenario = Column(String(200), nullable=False, comment="使用场景")
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
