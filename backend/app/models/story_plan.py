from sqlalchemy import Column, String, JSON, Text, DateTime, Integer
from sqlalchemy.dialects.postgresql import UUID
from .story_unit import Base
import uuid


class StoryPlan(Base):
    __tablename__ = "story_plans"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    title = Column(String(500), nullable=False)
    story_outline = Column(Text, nullable=False)
    characters = Column(JSON)
    structure_type = Column(String(50), nullable=False)
    phases_data = Column(JSON)
    total_scene_count = Column(Integer, default=0)
    status = Column(String(50), default="draft")
    created_at = Column(DateTime, nullable=False)
    updated_at = Column(DateTime, nullable=False)
