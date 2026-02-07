from pydantic import BaseModel, Field, field_serializer
from typing import List, Optional, Dict, Any
from uuid import UUID


class EmotionUpdateRequest(BaseModel):
    emotion_type: str = Field(..., description="情绪类型")
    intensity: float = Field(..., ge=0, le=10, description="情绪强度(0-10)")
    decay_rate: float = Field(0.1, ge=0, le=1, description="衰减率")


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


class CharacterUpdate(BaseModel):
    core_personality: Optional[Dict[str, Any]] = Field(None, description="核心性格")
    background: Optional[str] = Field(None, description="背景设定")
    bottom_line: Optional[Dict[str, Any]] = Field(None, description="底线")
    current_emotion: Optional[Dict[str, Any]] = Field(None, description="当前情绪")
    goals: Optional[Dict[str, Any]] = Field(None, description="目标")
    relationships: Optional[Dict[str, Any]] = Field(None, description="关系")


class CharacterResponse(CharacterBase):
    id: UUID
    created_at: Optional[str] = None
    updated_at: Optional[str] = None

    @field_serializer('id')
    def serialize_id(self, value: UUID, _info):
        return str(value)

    class Config:
        from_attributes = True


class ScriptGenerationRequest(BaseModel):
    plot_context: str = Field(..., description="剧情上下文")
    required_conflict: str = Field(..., description="需要的冲突类型")
    required_emotion: str = Field(..., description="需要的情绪类型")
    characters: List[str] = Field(..., description="出场人物")
    scene: Optional[str] = Field(None, description="场景")
    constraints: Optional[Dict[str, Any]] = Field(None, description="生成约束")
    goal_driven: bool = Field(False, description="是否启用目标驱动生成")
    style: Optional[str] = Field("standard", description="剧本风格：standard（标准）、humorous（幽默）、serious（严肃）、romantic（浪漫）")
    length: Optional[str] = Field("medium", description="剧本长度：short（短，300-500字）、medium（中，500-800字）、long（长，800-1200字）")
    innovation_degree: Optional[float] = Field(0.5, ge=0.0, le=1.0, description="创新程度：0.0（保守，贴近参考）到1.0（创新，突破常规）")
    enable_quality_evaluation: bool = Field(False, description="是否启用多维度质量评估")


class ScriptGenerationResponse(BaseModel):
    generated_script: str
    referenced_units: List[str]
    confidence: float
    applied_character_constraints: Optional[List[str]] = None
    temporal_context: Optional[Dict[str, Any]] = None
    quality_evaluation: Optional[Dict[str, Any]] = Field(None, description="多维度质量评估结果（当 enable_quality_evaluation=True 时返回）")


class ScriptEvaluationRequest(BaseModel):
    script: str = Field(..., description="待评估的剧本")
    constraints: Optional[Dict[str, Any]] = Field(None, description="生成约束")


class ScriptEvaluationResponse(BaseModel):
    conflict_intensity: int
    emotion_rendering: int
    character_consistency: int
    dialogue_naturalness: int
    dramatic_tension: int
    plot_coherence: int
    word_count_control: int
    overall_score: float
    quality_level: str
    strengths: List[str]
    weaknesses: List[str]
    suggestions: List[str]


class BatchScriptGenerationRequest(BaseModel):
    plot_context: str = Field(..., description="剧情上下文")
    required_conflict: str = Field(..., description="需要的冲突类型")
    required_emotion: str = Field(..., description="需要的情绪类型")
    characters: List[str] = Field(..., description="出场人物")
    scene: Optional[str] = Field(None, description="场景")
    constraints: Optional[Dict[str, Any]] = Field(None, description="生成约束")
    goal_driven: bool = Field(False, description="是否启用目标驱动生成")
    style: Optional[str] = Field("standard", description="剧本风格：standard（标准）、humorous（幽默）、serious（严肃）、romantic（浪漫）")
    length: Optional[str] = Field("medium", description="剧本长度：short（短，300-500字）、medium（中，500-800字）、long（长，800-1200字）")
    innovation_degree: Optional[float] = Field(0.5, ge=0.0, le=1.0, description="创新程度：0.0（保守，贴近参考）到1.0（创新，突破常规）")
    batch_size: int = Field(3, ge=1, le=10, description="批次生成数量（1-10）")
    return_best_only: bool = Field(False, description="是否仅返回最佳剧本")
    enable_quality_evaluation: bool = Field(False, description="是否启用多维度质量评估")


class BatchScriptGenerationResponse(BaseModel):
    scripts: List[ScriptGenerationResponse]
    best_script_index: Optional[int] = Field(None, description="最佳剧本索引，当 return_best_only=True 时为0")
    total_count: int
    generation_time_seconds: float
