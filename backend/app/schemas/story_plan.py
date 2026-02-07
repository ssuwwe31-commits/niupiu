from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field
from datetime import datetime


class ScenePlan(BaseModel):
    scene_number: int = Field(..., description="场次序号")
    phase: str = Field(..., description="所属阶段")
    scene_description: str = Field(..., description="场景描述")
    core_conflict: str = Field(..., description="核心冲突")
    emotion_goal: str = Field(..., description="情绪目标")
    main_characters: List[str] = Field(default_factory=list, description="主要人物")
    plot_function: str = Field(..., description="剧情功能")
    key_event: str = Field(..., description="关键事件")


class StoryPhase(BaseModel):
    name: str = Field(..., description="阶段名称")
    description: str = Field(..., description="阶段描述")
    scene_count: int = Field(..., description="该阶段场次数")
    scenes: List[ScenePlan] = Field(default_factory=list, description="该阶段的场景规划")


class StoryPlanRequest(BaseModel):
    story_outline: str = Field(..., description="故事梗概", min_length=10)
    characters: List[str] = Field(..., description="人物列表", min_items=1)
    structure_type: str = Field(default="three_act", description="剧情结构类型")
    total_scene_count: Optional[int] = Field(None, description="总场次数量")
    custom_phase_distribution: Optional[Dict[str, int]] = Field(None, description="自定义各阶段场次分布")


class StoryPlanResponse(BaseModel):
    plan_id: str = Field(..., description="规划 ID")
    story_outline: str = Field(..., description="故事梗概")
    characters: List[str] = Field(..., description="人物列表")
    structure_type: str = Field(..., description="剧情结构类型")
    created_at: str = Field(..., description="创建时间")
    phases: List[StoryPhase] = Field(..., description="剧情阶段")
    total_scene_count: int = Field(..., description="总场次数量")


class AdjustScenePlanRequest(BaseModel):
    plan_id: str = Field(..., description="规划 ID")
    scene_number: int = Field(..., description="场次序号")
    adjustments: Dict[str, Any] = Field(..., description="调整内容")


class AdjustScenePlanResponse(BaseModel):
    plan_id: str = Field(..., description="规划 ID")
    scene_number: int = Field(..., description="场次序号")
    adjustments: Dict[str, Any] = Field(..., description="调整内容")
    status: str = Field(..., description="状态")


class GenerateFullScriptRequest(BaseModel):
    plan_id: str = Field(..., description="规划 ID")
    style: str = Field(default="standard", description="剧本风格")
    length: str = Field(default="medium", description="剧本长度")
    innovation_degree: float = Field(default=0.5, ge=0.0, le=1.0, description="创新程度")


class GeneratedScene(BaseModel):
    scene_number: int = Field(..., description="场次序号")
    scene_description: str = Field(..., description="场景描述")
    script: str = Field(..., description="生成的剧本内容")
    confidence: float = Field(..., description="置信度")


class GenerateFullScriptResponse(BaseModel):
    plan_id: str = Field(..., description="规划 ID")
    generated_scenes: List[GeneratedScene] = Field(..., description="生成的剧本")
    total_scene_count: int = Field(..., description="总场次数量")
    generation_time_seconds: float = Field(..., description="生成耗时（秒）")


class StructureTemplateInfo(BaseModel):
    id: str = Field(..., description="模板 ID")
    name: str = Field(..., description="模板名称")
    phases: List[Dict[str, Any]] = Field(..., description="阶段信息")


class SaveStoryPlanRequest(BaseModel):
    title: str = Field(..., description="规划标题", min_length=1, max_length=500)
    story_outline: str = Field(..., description="故事梗概", min_length=10)
    characters: List[str] = Field(..., description="人物列表", min_items=1)
    structure_type: str = Field(default="three_act", description="剧情结构类型")
    phases_data: List[StoryPhase] = Field(..., description="剧情阶段数据")
    total_scene_count: int = Field(..., description="总场次数量")
    status: str = Field(default="draft", description="状态")


class SaveStoryPlanResponse(BaseModel):
    id: str = Field(..., description="规划 ID")
    title: str = Field(..., description="规划标题")
    story_outline: str = Field(..., description="故事梗概")
    characters: List[str] = Field(..., description="人物列表")
    structure_type: str = Field(..., description="剧情结构类型")
    phases_data: List[StoryPhase] = Field(..., description="剧情阶段数据")
    total_scene_count: int = Field(..., description="总场次数量")
    status: str = Field(..., description="状态")
    created_at: datetime = Field(..., description="创建时间")
    updated_at: datetime = Field(..., description="更新时间")


class UpdateStoryPlanRequest(BaseModel):
    title: Optional[str] = Field(None, min_length=1, max_length=500, description="规划标题")
    story_outline: Optional[str] = Field(None, min_length=10, description="故事梗概")
    characters: Optional[List[str]] = Field(None, min_items=1, description="人物列表")
    structure_type: Optional[str] = Field(None, description="剧情结构类型")
    phases_data: Optional[List[StoryPhase]] = Field(None, description="剧情阶段数据")
    total_scene_count: Optional[int] = Field(None, description="总场次数量")
    status: Optional[str] = Field(None, description="状态")


class StoryPlanListItem(BaseModel):
    id: str = Field(..., description="规划 ID")
    title: str = Field(..., description="规划标题")
    story_outline: str = Field(..., description="故事梗概")
    structure_type: str = Field(..., description="剧情结构类型")
    total_scene_count: int = Field(..., description="总场次数量")
    status: str = Field(..., description="状态")
    created_at: datetime = Field(..., description="创建时间")
    updated_at: datetime = Field(..., description="更新时间")


class UpdateStoryPlanResponse(BaseModel):
    id: str = Field(..., description="规划 ID")
    title: str = Field(..., description="规划标题")
    story_outline: str = Field(..., description="故事梗概")
    characters: List[str] = Field(..., description="人物列表")
    structure_type: str = Field(..., description="剧情结构类型")
    phases_data: List[StoryPhase] = Field(..., description="剧情阶段数据")
    total_scene_count: int = Field(..., description="总场次数量")
    status: str = Field(..., description="状态")
    updated_at: datetime = Field(..., description="更新时间")


class StoryPlanListResponse(BaseModel):
    items: List[SaveStoryPlanResponse] = Field(..., description="规划列表")
    total: int = Field(..., description="总数")
    skip: int = Field(..., description="跳过数量")
    limit: int = Field(..., description="限制数量")