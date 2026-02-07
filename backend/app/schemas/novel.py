from pydantic import BaseModel, field_serializer
from typing import Optional
from datetime import datetime
from uuid import UUID


class NovelCreate(BaseModel):
    title: str
    author: Optional[str] = None
    file_type: str
    file_size: int
    summary: Optional[str] = None


class NovelResponse(BaseModel):
    id: UUID
    title: str
    author: Optional[str]
    file_path: str
    file_type: str
    file_size: int
    total_chapters: int
    total_units: int
    status: str
    summary: Optional[str]
    created_at: datetime
    updated_at: datetime

    @field_serializer('id')
    def serialize_id(self, value: UUID, _info):
        return str(value)

    class Config:
        from_attributes = True


class NovelDecomposeRequest(BaseModel):
    chapter_range: Optional[tuple[int, int]] = None


class NovelDecomposeResponse(BaseModel):
    novel_id: str
    total_units: int
    success_count: int
    failed_count: int
    message: str
