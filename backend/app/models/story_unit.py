from sqlalchemy import Column, String, JSON, Text, Float, Integer
from sqlalchemy.dialects.postgresql import UUID, ARRAY
from sqlalchemy.ext.declarative import declarative_base
import uuid

Base = declarative_base()


class StoryUnit(Base):
    __tablename__ = "story_units"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    scene = Column(String(255), nullable=False)
    characters = Column(ARRAY(String), nullable=False)
    core_conflict = Column(String(255), nullable=False)
    emotion_curve = Column(ARRAY(String), nullable=False)
    plot_function = Column(String(255), nullable=False)
    result = Column(String(255))
    original_text = Column(Text, nullable=False)
    embedding = Column(ARRAY(Float))

    conflict_type = Column(String(100))
    emotion_type = Column(String(100))
    character_relationship = Column(String(100))
    time_position = Column(String(100))
    pre_dependencies = Column(JSON)
    post_effects = Column(JSON)

    source_novel_id = Column(UUID(as_uuid=True))
    chapter = Column(Integer)
    confidence_score = Column(Float, default=0.0)
