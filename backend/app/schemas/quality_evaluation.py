from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional


class DimensionScore(BaseModel):
    score: float = Field(..., ge=0, le=10, description="维度评分")
    reasoning: str = Field(default="", description="评分理由")
    strengths: List[str] = Field(default_factory=list, description="优点")
    weaknesses: List[str] = Field(default_factory=list, description="不足")


class QualityEvaluationRequest(BaseModel):
    script_content: str = Field(..., description="剧本内容", min_length=50)
    plot_context: Optional[str] = Field(None, description="剧情背景")
    characters: Optional[List[str]] = Field(None, description="出场人物列表")
    custom_weights: Optional[Dict[str, float]] = Field(None, description="自定义评分权重")
    reference_script: Optional[str] = Field(None, description="参考剧本")


class QualityEvaluationResponse(BaseModel):
    overall_score: float = Field(..., ge=0, le=10, description="综合评分")
    conflict_intensity: DimensionScore = Field(..., description="冲突强度评估")
    emotion_rendering: DimensionScore = Field(..., description="情绪渲染评估")
    character_consistency: DimensionScore = Field(..., description="人物一致性评估")
    dialogue_naturalness: DimensionScore = Field(..., description="对话自然度评估")
    dramatic_tension: DimensionScore = Field(..., description="剧情张力评估")
    overall_coherence: DimensionScore = Field(..., description="整体连贯性评估")
    weights_used: Dict[str, float] = Field(default_factory=dict, description="使用的评分权重")
    comparison_with_reference: Optional[DimensionScore] = Field(None, description="与参考剧本的比较")
    quality_level: str = Field(..., description="质量等级", examples=["excellent", "good", "acceptable", "poor"])


class BatchEvaluationScript(BaseModel):
    id: Optional[str] = Field(None, description="剧本ID")
    content: str = Field(..., description="剧本内容")
    plot_context: Optional[str] = Field(None, description="剧情背景")
    characters: Optional[List[str]] = Field(None, description="出场人物列表")


class BatchEvaluationRequest(BaseModel):
    scripts: List[BatchEvaluationScript] = Field(..., description="待评估的剧本列表", min_items=1, max_items=20)
    custom_weights: Optional[Dict[str, float]] = Field(None, description="自定义评分权重")


class ScriptEvaluationResult(BaseModel):
    script_id: str = Field(..., description="剧本ID")
    evaluation: QualityEvaluationResponse = Field(..., description="评估结果")


class BatchEvaluationResponse(BaseModel):
    total_count: int = Field(..., description="总剧本数")
    results: List[ScriptEvaluationResult] = Field(..., description="所有评估结果")
    ranked_scripts: List[str] = Field(..., description="按评分排序的剧本ID列表")
    best_script: Optional[ScriptEvaluationResult] = Field(None, description="最佳剧本")


class MetricDescription(BaseModel):
    name: str = Field(..., description="维度名称")
    display_name: str = Field(..., description="显示名称")
    description: str = Field(..., description="维度描述")
    weight: float = Field(..., ge=0, le=1, description="默认权重")
    score_range: str = Field(..., description="分数范围")


class MetricsResponse(BaseModel):
    metrics: List[MetricDescription] = Field(..., description="评估维度列表")
    overall_score: Dict[str, str] = Field(..., description="综合评分说明")
    quality_thresholds: Dict[str, str] = Field(..., description="质量等级阈值")


class AutoEvaluationConfig(BaseModel):
    enabled: bool = Field(default=True, description="是否启用自动评估")
    min_score_threshold: float = Field(default=6.0, ge=0, le=10, description="最低合格分数")
    max_regeneration_attempts: int = Field(default=3, ge=1, le=10, description="最大重新生成次数")
    batch_size: int = Field(default=5, ge=1, le=20, description="批量生成时的样本数")
    select_best: bool = Field(default=True, description="是否选择最佳结果")
