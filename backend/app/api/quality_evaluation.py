from fastapi import APIRouter, Depends, HTTPException
from app.schemas.quality_evaluation import (
    QualityEvaluationRequest,
    QualityEvaluationResponse,
    BatchEvaluationRequest,
    BatchEvaluationResponse,
    MetricsResponse,
    AutoEvaluationConfig
)
from app.services.quality_evaluator import quality_evaluator
from typing import Dict, Any

router = APIRouter(prefix="/api/quality", tags=["quality_evaluation"])


@router.post("/evaluate", response_model=QualityEvaluationResponse)
async def evaluate_script_quality(request: QualityEvaluationRequest):
    """
    评估单个剧本质量

    评估维度：
    - conflict_intensity: 冲突强度（权重20%）
    - emotion_rendering: 情绪渲染（权重15%）
    - character_consistency: 人物一致性（权重20%）
    - dialogue_naturalness: 对话自然度（权重15%）
    - dramatic_tension: 剧情张力（权重15%）
    - overall_coherence: 整体连贯性（权重15%）

    支持自定义评分权重，传入 custom_weights 参数覆盖默认权重
    """
    try:
        result = await quality_evaluator.evaluate_script(
            script_content=request.script_content,
            plot_context=request.plot_context,
            characters=request.characters,
            custom_weights=request.custom_weights,
            reference_script=request.reference_script
        )

        overall_score = result.get("overall_score", 5.0)
        quality_level = _determine_quality_level(overall_score)

        return QualityEvaluationResponse(
            overall_score=overall_score,
            conflict_intensity=result["conflict_intensity"],
            emotion_rendering=result["emotion_rendering"],
            character_consistency=result["character_consistency"],
            dialogue_naturalness=result["dialogue_naturalness"],
            dramatic_tension=result["dramatic_tension"],
            overall_coherence=result["overall_coherence"],
            weights_used=result.get("weights_used", {}),
            comparison_with_reference=result.get("comparison_with_reference"),
            quality_level=quality_level
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"评估失败: {str(e)}")


@router.post("/evaluate-batch", response_model=BatchEvaluationResponse)
async def evaluate_batch_scripts(request: BatchEvaluationRequest):
    """
    批量评估剧本质量

    最多支持20个剧本同时评估，自动按综合评分排序返回
    """
    try:
        result = await quality_evaluator.evaluate_batch(
            scripts=[script.dict() for script in request.scripts],
            custom_weights=request.custom_weights
        )

        return BatchEvaluationResponse(
            total_count=result["total_count"],
            results=[
                {
                    "script_id": r["script_id"],
                    "evaluation": _convert_to_evaluation_response(r["evaluation"])
                }
                for r in result["results"]
            ],
            ranked_scripts=result["ranked_scripts"],
            best_script={
                "script_id": result["best_script"]["script_id"],
                "evaluation": _convert_to_evaluation_response(result["best_script"]["evaluation"])
            } if result["best_script"] else None
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"批量评估失败: {str(e)}")


@router.get("/metrics", response_model=MetricsResponse)
async def get_evaluation_metrics():
    """
    获取评估指标说明

    返回所有评估维度的详细说明，包括：
    - 维度名称和显示名称
    - 维度描述
    - 默认权重
    - 分数范围
    - 质量等级阈值
    """
    try:
        description = quality_evaluator.get_metrics_description()
        return MetricsResponse(**description)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取指标失败: {str(e)}")


@router.get("/health")
async def health_check():
    """
    健康检查
    """
    return {"status": "healthy", "service": "quality_evaluation"}


def _determine_quality_level(score: float) -> str:
    if score >= 8.0:
        return "excellent"
    elif score >= 6.5:
        return "good"
    elif score >= 5.0:
        return "acceptable"
    else:
        return "poor"


def _convert_to_evaluation_response(evaluation: Dict[str, Any]) -> QualityEvaluationResponse:
    overall_score = evaluation.get("overall_score", 5.0)
    quality_level = _determine_quality_level(overall_score)

    return QualityEvaluationResponse(
        overall_score=overall_score,
        conflict_intensity=evaluation["conflict_intensity"],
        emotion_rendering=evaluation["emotion_rendering"],
        character_consistency=evaluation["character_consistency"],
        dialogue_naturalness=evaluation["dialogue_naturalness"],
        dramatic_tension=evaluation["dramatic_tension"],
        overall_coherence=evaluation["overall_coherence"],
        weights_used=evaluation.get("weights_used", {}),
        comparison_with_reference=evaluation.get("comparison_with_reference"),
        quality_level=quality_level
    )
