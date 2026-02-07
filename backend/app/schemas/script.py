from pydantic import BaseModel, Field, field_serializer
from typing import List, Optional, Dict, Any
from datetime import datetime
from uuid import UUID


class ScriptGenerationRequest(BaseModel):
    plot_context: str = Field(..., description="剧情上下文", min_length=10)
    required_conflict: str = Field(..., description="需要的冲突类型", examples=["误会", "背叛", "利益", "价值观"])
    required_emotion: str = Field(..., description="需要的情绪类型", examples=["尴尬", "紧张", "焦虑", "愤怒"])
    characters: List[str] = Field(..., description="出场人物", min_items=1)
    scene: Optional[str] = Field(None, description="场景", examples=["教学楼天台", "会议室", "客厅"])
    constraints: Optional[Dict[str, Any]] = Field(None, description="生成约束")
    goal_driven: bool = Field(False, description="是否启用目标驱动生成")
    reference_count: int = Field(3, ge=1, le=10, description="参考剧情单元数量")
    style: str = Field("standard", description="剧本风格", examples=["standard", "humorous", "serious", "romantic"])
    length: str = Field("medium", description="剧本长度", examples=["short", "medium", "long"])
    innovation_degree: float = Field(0.5, ge=0, le=1, description="创新程度")
    enable_quality_evaluation: bool = Field(False, description="是否启用质量评估")


class ScriptGenerationResponse(BaseModel):
    generated_script: str = Field(..., description="生成的剧本内容")
    referenced_units: List[str] = Field(default_factory=list, description="参考的剧情单元ID列表")
    confidence: float = Field(..., ge=0, le=1, description="生成置信度")
    applied_character_constraints: Optional[List[str]] = Field(None, description="应用的人物约束")
    temporal_context: Optional[Dict[str, Any]] = Field(None, description="时序上下文")
    active_goals: Optional[List[Dict[str, Any]]] = Field(None, description="活跃的目标")
    generation_metadata: Optional[Dict[str, Any]] = Field(None, description="生成元数据")
    evaluation: Optional[Dict[str, Any]] = Field(None, description="质量评估结果")


class ScriptEvaluationRequest(BaseModel):
    script: str = Field(..., description="待评估的剧本", min_length=50)
    constraints: Optional[Dict[str, Any]] = Field(None, description="生成约束")
    evaluation_aspects: Optional[List[str]] = Field(None, description="评估维度")


class ScriptEvaluationResponse(BaseModel):
    conflict_intensity: int = Field(..., ge=0, le=10, description="冲突强度")
    emotion_rendering: int = Field(..., ge=0, le=10, description="情绪渲染")
    character_consistency: int = Field(..., ge=0, le=10, description="人物一致性")
    dialogue_naturalness: int = Field(..., ge=0, le=10, description="对话自然度")
    dramatic_tension: int = Field(..., ge=0, le=10, description="戏剧张力")
    plot_coherence: int = Field(..., ge=0, le=10, description="情节连贯性")
    word_count_control: int = Field(..., ge=0, le=10, description="字数控制")
    overall_score: float = Field(..., ge=0, le=10, description="总体评分")
    quality_level: str = Field(..., description="质量等级", examples=["优秀", "良好", "一般", "较差"])
    strengths: List[str] = Field(default_factory=list, description="优点")
    weaknesses: List[str] = Field(default_factory=list, description="不足")
    suggestions: List[str] = Field(default_factory=list, description="建议")


class ScriptUnit(BaseModel):
    """单个剧本单元"""
    scene: str = Field(..., description="场景")
    characters: List[str] = Field(..., description="出场人物")
    core_conflict: str = Field(..., description="核心冲突")
    emotion_curve: List[str] = Field(..., description="情绪曲线")
    plot_function: str = Field(..., description="剧情功能")
    result: Optional[str] = Field(None, description="结果")
    dialogue: Optional[List[Dict[str, Any]]] = Field(None, description="对话内容")
    action_description: Optional[str] = Field(None, description="动作描述")


class ScriptMetadata(BaseModel):
    """剧本元数据"""
    id: Optional[UUID] = Field(None, description="剧本ID")
    title: Optional[str] = Field(None, description="剧本标题")
    genre: Optional[str] = Field(None, description="类型", examples=["青春校园", "职场", "家庭"])
    created_at: Optional[datetime] = Field(None, description="创建时间")
    updated_at: Optional[datetime] = Field(None, description="更新时间")
    version: Optional[int] = Field(1, description="版本号")
    author: Optional[str] = Field(None, description="作者")

    @field_serializer('id')
    def serialize_id(self, value: Optional[UUID], _info):
        return str(value) if value else None


class ScriptCreate(BaseModel):
    """创建剧本"""
    title: str = Field(..., description="剧本标题")
    genre: str = Field(..., description="类型")
    plot_context: str = Field(..., description="剧情上下文")
    units: List[ScriptUnit] = Field(..., description="剧本单元列表")
    metadata: Optional[Dict[str, Any]] = Field(None, description="附加元数据")


class ScriptUpdate(BaseModel):
    """更新剧本"""
    title: Optional[str] = Field(None, description="剧本标题")
    genre: Optional[str] = Field(None, description="类型")
    plot_context: Optional[str] = Field(None, description="剧情上下文")
    units: Optional[List[ScriptUnit]] = Field(None, description="剧本单元列表")
    metadata: Optional[Dict[str, Any]] = Field(None, description="附加元数据")


class ScriptResponse(BaseModel):
    """剧本响应"""
    id: UUID
    title: str
    genre: str
    plot_context: str
    units: List[ScriptUnit]
    metadata: ScriptMetadata
    created_at: datetime
    updated_at: Optional[datetime] = None

    @field_serializer('id')
    def serialize_id(self, value: UUID, _info):
        return str(value)

    class Config:
        from_attributes = True


class ScriptSearch(BaseModel):
    """剧本搜索"""
    genre: Optional[str] = Field(None, description="类型")
    conflict_type: Optional[str] = Field(None, description="冲突类型")
    emotion_type: Optional[str] = Field(None, description="情绪类型")
    character_name: Optional[str] = Field(None, description="人物名称")
    query: Optional[str] = Field(None, description="向量检索查询")
    top_k: int = Field(10, ge=1, le=50, description="返回数量")
