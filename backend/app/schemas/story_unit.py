from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from datetime import datetime


class StoryUnitBase(BaseModel):
    scene: str = Field(..., description="场景")
    characters: List[str] = Field(..., description="出场人物")
    core_conflict: str = Field(..., description="核心冲突")
    emotion_curve: List[str] = Field(..., description="情绪曲线")
    plot_function: str = Field(..., description="剧情功能")
    result: Optional[str] = Field(None, description="结果")
    original_text: str = Field(..., description="原始文本")
    conflict_type: Optional[str] = Field(None, description="冲突类型")
    emotion_type: Optional[str] = Field(None, description="情绪类型")
    character_relationship: Optional[str] = Field(None, description="人物关系")
    time_position: Optional[str] = Field(None, description="时间位置")
    pre_dependencies: Optional[Dict[str, Any]] = Field(None, description="前置依赖")
    post_effects: Optional[Dict[str, Any]] = Field(None, description="后置影响")
    chapter: Optional[int] = Field(None, description="章节")
    confidence_score: Optional[float] = Field(0.0, description="置信度")


class StoryUnitCreate(StoryUnitBase):
    pass


class StoryUnitResponse(StoryUnitBase):
    id: str
    created_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class StoryUnitSearch(BaseModel):
    conflict_type: Optional[str] = Field(None, description="冲突类型")
    emotion_type: Optional[str] = Field(None, description="情绪类型")
    character_relationship: Optional[str] = Field(None, description="人物关系")
    plot_function: Optional[str] = Field(None, description="剧情功能")
    query: Optional[str] = Field(None, description="向量检索查询")
    top_k: int = Field(5, description="返回数量")
