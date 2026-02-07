from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.db.database import get_db
from app.models.story_unit import StoryUnit
from app.models.character import Character
from app.schemas.story_unit import StoryUnitCreate, StoryUnitResponse, StoryUnitSearch, StoryUnitUpdate
from app.schemas.character import (
    ScriptGenerationRequest, ScriptGenerationResponse, 
    ScriptEvaluationRequest, ScriptEvaluationResponse,
    BatchScriptGenerationRequest, BatchScriptGenerationResponse
)
from app.schemas.quality_evaluation import (
    QualityEvaluationRequest, QualityEvaluationResponse,
    BatchEvaluationRequest, BatchEvaluationResponse
)
from app.services.rag_service import rag_service
from app.services.script_service import script_service
from app.services.quality_evaluator import quality_evaluator
from typing import List, Optional, Tuple, Dict, Any
from pydantic import BaseModel, Field

router = APIRouter(prefix="/api", tags=["script"])


@router.post("/story-units", response_model=StoryUnitResponse)
async def create_story_unit(
    story_unit: StoryUnitCreate,
    db: AsyncSession = Depends(get_db)
):
    from app.db.database import init_db
    from app.services.ollama_client import get_ollama_manager

    await init_db()

    db_story_unit = StoryUnit(**story_unit.dict())
    db.add(db_story_unit)
    await db.commit()
    await db.refresh(db_story_unit)

    ollama_manager = get_ollama_manager()
    embed_model = ollama_manager.embed_model
    text = f"{db_story_unit.scene} {db_story_unit.core_conflict} {db_story_unit.original_text}"
    embedding = embed_model.get_text_embedding(text)
    db_story_unit.embedding = embedding
    await db.commit()
    await db.refresh(db_story_unit)

    return db_story_unit


@router.get("/story-units/{unit_id}", response_model=StoryUnitResponse)
async def get_story_unit(unit_id: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(StoryUnit).where(StoryUnit.id == unit_id))
    story_unit = result.scalar_one_or_none()
    if not story_unit:
        raise HTTPException(status_code=404, detail="Story unit not found")
    return story_unit


@router.put("/story-units/{unit_id}", response_model=StoryUnitResponse)
async def update_story_unit(
    unit_id: str,
    update_data: StoryUnitUpdate,
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(select(StoryUnit).where(StoryUnit.id == unit_id))
    story_unit = result.scalar_one_or_none()
    if not story_unit:
        raise HTTPException(status_code=404, detail="Story unit not found")
    
    if update_data.embedding is not None:
        story_unit.embedding = update_data.embedding
    
    await db.commit()
    await db.refresh(story_unit)
    return story_unit


@router.get("/story-units", response_model=List[StoryUnitResponse])
async def list_story_units(
    skip: int = 0,
    limit: int = 100,
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(
        select(StoryUnit).offset(skip).limit(limit)
    )
    story_units = result.scalars().all()
    return story_units


@router.post("/story-units/search")
async def search_story_units(search_params: StoryUnitSearch):
    results = await rag_service.search_story_units(
        query=search_params.query,
        conflict_type=search_params.conflict_type,
        emotion_type=search_params.emotion_type,
        character_relationship=search_params.character_relationship,
        plot_function=search_params.plot_function,
        top_k=search_params.top_k,
        fusion_method=search_params.fusion_method,
        vector_weight=search_params.vector_weight,
        metadata_weight=search_params.metadata_weight,
        rrf_k=search_params.rrf_k,
    )
    return {"results": results}


@router.post("/generate-script-deepseek", response_model=ScriptGenerationResponse)
async def generate_script_deepseek(request: ScriptGenerationRequest):
    """
    使用 DeepSeek 生成剧本
    """
    try:
        result = await script_service.generate_script(
            plot_context=request.plot_context,
            required_conflict=request.required_conflict,
            required_emotion=request.required_emotion,
            characters=request.characters,
            scene=request.scene,
            constraints=request.constraints,
            goal_driven=request.goal_driven,
            style=request.style,
            length=request.length,
            innovation_degree=request.innovation_degree,
            enable_quality_evaluation=request.enable_quality_evaluation,
        )
        return result
    except RuntimeError as e:
        raise HTTPException(status_code=503, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@router.post("/evaluate-script-deepseek", response_model=ScriptEvaluationResponse)
async def evaluate_script_deepseek(request: ScriptEvaluationRequest):
    """
    使用 DeepSeek 评估剧本质量
    """
    try:
        result = await script_service.evaluate_script_quality(
            script=request.script,
            constraints=request.constraints
        )
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@router.post("/generate-script-batch", response_model=BatchScriptGenerationResponse)
async def generate_script_batch(request: BatchScriptGenerationRequest):
    """
    批次生成剧本
    """
    try:
        result = await script_service.generate_script_batch(
            plot_context=request.plot_context,
            required_conflict=request.required_conflict,
            required_emotion=request.required_emotion,
            characters=request.characters,
            scene=request.scene,
            constraints=request.constraints,
            goal_driven=request.goal_driven,
            style=request.style,
            length=request.length,
            innovation_degree=request.innovation_degree,
            batch_size=request.batch_size,
            return_best_only=request.return_best_only,
            enable_quality_evaluation=request.enable_quality_evaluation,
        )
        return result
    except RuntimeError as e:
        raise HTTPException(status_code=503, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@router.post("/generate-script", response_model=ScriptGenerationResponse)
async def generate_script(request: ScriptGenerationRequest):
    try:
        result = await rag_service.generate_script(
            plot_context=request.plot_context,
            required_conflict=request.required_conflict,
            required_emotion=request.required_emotion,
            characters=request.characters,
            scene=request.scene,
            constraints=request.constraints,
            goal_driven=request.goal_driven,
        )
        return result
    except RuntimeError as e:
        raise HTTPException(status_code=503, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


class TemporalSearchRequest(BaseModel):
    target_unit_id: Optional[str] = None
    chapter_range: Optional[Tuple[int, int]] = None
    preceding_units: int = 0
    subsequent_units: int = 0
    top_k: int = 10


@router.post("/temporal-units/search")
async def search_temporal_units(request: TemporalSearchRequest):
    try:
        results = await rag_service.search_temporal_units(
            target_unit_id=request.target_unit_id,
            chapter_range=request.chapter_range,
            preceding_units=request.preceding_units,
            subsequent_units=request.subsequent_units,
            top_k=request.top_k,
        )
        return results
    except RuntimeError as e:
        raise HTTPException(status_code=503, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


class ScriptGenerationWithTemporalRequest(BaseModel):
    plot_context: str
    required_conflict: str
    required_emotion: str
    characters: List[str]
    scene: Optional[str] = None
    constraints: Optional[Dict[str, Any]] = None
    temporal_context: Optional[Dict[str, Any]] = None


class ConflictResolutionRequest(BaseModel):
    characters: List[str] = Field(..., description="参与冲突协调的角色列表")
    scene_context: Optional[str] = Field(None, description="场景上下文描述")


@router.post("/generate-script-with-temporal", response_model=ScriptGenerationResponse)
async def generate_script_with_temporal(request: ScriptGenerationWithTemporalRequest):
    try:
        result = await rag_service.generate_script_with_temporal(
            plot_context=request.plot_context,
            required_conflict=request.required_conflict,
            required_emotion=request.required_emotion,
            characters=request.characters,
            scene=request.scene,
            constraints=request.constraints,
            temporal_context=request.temporal_context,
        )
        return result
    except RuntimeError as e:
        raise HTTPException(status_code=503, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@router.post("/evaluate-script", response_model=ScriptEvaluationResponse)
async def evaluate_script(request: ScriptEvaluationRequest):
    try:
        result = await rag_service.evaluate_script_quality(
            script=request.script,
            constraints=request.constraints or {}
        )
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/quality-evaluate", response_model=QualityEvaluationResponse)
async def quality_evaluate_script(request: QualityEvaluationRequest):
    """
    多维度剧本质量评估
    
    提供以下维度的评分：
    - 冲突强度
    - 情绪渲染
    - 人物一致性
    - 对话自然度
    - 剧情张力
    - 整体连贯性
    """
    try:
        result = await quality_evaluator.evaluate_script(
            script_content=request.script_content,
            plot_context=request.plot_context,
            characters=request.characters,
            custom_weights=request.custom_weights,
            reference_script=request.reference_script
        )
        return result
    except RuntimeError as e:
        raise HTTPException(status_code=503, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@router.post("/quality-evaluate-batch", response_model=BatchEvaluationResponse)
async def quality_evaluate_batch(request: BatchEvaluationRequest):
    """
    批量剧本质量评估
    
    支持对多个剧本进行并行评估，提高评估效率
    """
    try:
        result = await quality_evaluator.evaluate_batch(
            scripts=request.scripts,
            plot_context=request.plot_context,
            characters=request.characters,
            custom_weights=request.custom_weights,
            reference_script=request.reference_script
        )
        return result
    except RuntimeError as e:
        raise HTTPException(status_code=503, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@router.get("/health")
async def health_check():
    return {"status": "healthy"}


@router.post("/resolve-conflicts")
async def resolve_character_conflicts(request: ConflictResolutionRequest):
    try:
        result = await rag_service.resolve_character_conflicts(
            characters=request.characters,
            scene_context=request.scene_context
        )
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


class TemporalRelationRequest(BaseModel):
    source_unit_id: str = Field(..., description="源剧情单元ID")
    target_unit_id: str = Field(..., description="目标剧情单元ID")
    auto_update: bool = Field(False, description="是否自动更新到数据库")


@router.post("/temporal-relations/generate")
async def generate_temporal_relation(request: TemporalRelationRequest):
    try:
        result = await rag_service.generate_temporal_relations(
            source_unit_id=request.source_unit_id,
            target_unit_id=request.target_unit_id,
            auto_update=request.auto_update
        )
        return result
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


class BatchTemporalRelationRequest(BaseModel):
    unit_ids: List[str] = Field(..., description="剧情单元ID列表，按顺序排列")
    update_threshold: float = Field(0.7, ge=0, le=1, description="自动更新置信度阈值")


@router.post("/temporal-relations/batch-generate")
async def batch_generate_temporal_relations(request: BatchTemporalRelationRequest):
    try:
        result = await rag_service.batch_generate_temporal_relations(
            unit_ids=request.unit_ids,
            update_threshold=request.update_threshold
        )
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


class AutoLinkTemporalRequest(BaseModel):
    plot_context: str = Field(..., description="剧情上下文描述")
    characters: List[str] = Field(..., description="相关角色列表")
    look_back_units: int = Field(3, ge=0, description="向前回溯单元数")
    look_ahead_units: int = Field(1, ge=0, description="向前预览单元数")


@router.post("/temporal-relations/auto-link")
async def auto_link_temporal_context(request: AutoLinkTemporalRequest):
    try:
        result = await rag_service.auto_link_temporal_context(
            plot_context=request.plot_context,
            characters=request.characters,
            look_back_units=request.look_back_units,
            look_ahead_units=request.look_ahead_units
        )
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")
