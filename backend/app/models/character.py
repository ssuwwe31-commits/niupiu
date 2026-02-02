from sqlalchemy import Column, String, JSON, Text, Float, Integer
from sqlalchemy.dialects.postgresql import UUID
from .story_unit import Base
import uuid


class Character(Base):
    __tablename__ = "characters"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(255), nullable=False, unique=True)
    core_personality = Column(JSON)
    background = Column(Text)
    bottom_line = Column(JSON)
    current_emotion = Column(JSON)
    goals = Column(JSON)
    relationships = Column(JSON)
    created_at = Column(String(50))
    updated_at = Column(String(50))
