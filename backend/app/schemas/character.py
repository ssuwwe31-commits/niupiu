from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any


class CharacterBase(BaseModel):
    name: str = Field(..., description="角色名称")
    core_personality: Optional[Dict[str, Any]] = Field(None, description="核心性格")
    background: Optional[str] = Field(None, description="背景设定")
    bottom_line: Optional[Dict[str, Any]] = Field(None, description="底线")
    current_emotion: Optional[Dict[str, Any]] = Field(None, description="当前情绪")
    goals: Optional[Dict[str, Any]] = Field(None, description="目标")
    relationships: Optional[Dict[str, Any]] = Field(None, description="关系")


class CharacterCreate(CharacterBase):
    pass


class CharacterResponse(CharacterBase):
    id: str

    class Config:
        from_attributes = True


class ScriptGenerationRequest(BaseModel):
    plot_context: str = Field(..., description="剧情上下文")
    required_conflict: str = Field(..., description="需要的冲突类型")
    required_emotion: str = Field(..., description="需要的情绪类型")
    characters: List[str] = Field(..., description="出场人物")
    scene: Optional[str] = Field(None, description="场景")
    constraints: Optional[Dict[str, Any]] = Field(None, description="生成约束")


class ScriptGenerationResponse(BaseModel):
    generated_script: str
    referenced_units: List[str]
    confidence: float
