from fastapi import APIRouter, HTTPException, Depends
from typing import List, Optional
from app.schemas.story_plan import (
    StoryPlanRequest, StoryPlanResponse,
    AdjustScenePlanRequest, AdjustScenePlanResponse,
    GenerateFullScriptRequest, GenerateFullScriptResponse,
    StructureTemplateInfo,
    SaveStoryPlanRequest, SaveStoryPlanResponse,
    UpdateStoryPlanRequest, UpdateStoryPlanResponse,
    StoryPlanListResponse
)
from app.services.story_planner_service import story_planner_service
from app.services.script_service import script_service
from app.db.database import get_db
from app.db.story_plan_crud import StoryPlanCRUD
from sqlalchemy.ext.asyncio import AsyncSession
import time
import logging
import uuid

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/story-plan", tags=["story-plan"])


@router.get("/templates", response_model=List[StructureTemplateInfo])
async def get_structure_templates():
    """获取可用的剧情结构模板"""
    try:
        templates = story_planner_service.get_available_structure_templates()
        return [
            StructureTemplateInfo(
                id=template["id"],
                name=template["name"],
                phases=template["phases"]
            )
            for template in templates
        ]
    except Exception as e:
        logger.error(f"Failed to get structure templates: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to get structure templates: {str(e)}")


@router.post("/generate", response_model=StoryPlanResponse)
async def generate_story_plan(request: StoryPlanRequest):
    """生成剧情规划"""
    try:
        result = await story_planner_service.generate_story_plan(
            story_outline=request.story_outline,
            characters=request.characters,
            structure_type=request.structure_type,
            total_scene_count=request.total_scene_count,
            custom_phase_distribution=request.custom_phase_distribution
        )
        return StoryPlanResponse(**result)
    except ValueError as e:
        logger.error(f"Invalid request: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Failed to generate story plan: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to generate story plan: {str(e)}")


@router.post("/adjust-scene", response_model=AdjustScenePlanResponse)
async def adjust_scene_plan(request: AdjustScenePlanRequest):
    """调整某场戏的规划"""
    try:
        result = await story_planner_service.adjust_scene_plan(
            plan_id=request.plan_id,
            scene_number=request.scene_number,
            adjustments=request.adjustments
        )
        return AdjustScenePlanResponse(**result)
    except Exception as e:
        logger.error(f"Failed to adjust scene plan: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to adjust scene plan: {str(e)}")


@router.post("/generate-full-script", response_model=GenerateFullScriptResponse)
async def generate_full_script(request: GenerateFullScriptRequest, db: AsyncSession = Depends(get_db)):
    """根据剧情规划生成完整剧本"""
    try:
        start_time = time.time()

        logger.info(f"开始生成完整剧本: plan_id={request.plan_id}")

        plan = await StoryPlanCRUD.get_by_id(db, request.plan_id)
        if not plan:
            raise HTTPException(status_code=404, detail=f"Plan {request.plan_id} not found")

        phases_data = plan.phases_data
        if not phases_data:
            raise HTTPException(status_code=400, detail="Plan has no phases data")

        generated_scenes = []

        for phase in phases_data:
            for scene_plan in phase.get("scenes", []):
                try:
                    scene_desc = scene_plan.get("scene_description", "")
                    scene_characters = scene_plan.get("characters", plan.characters or [])
                    conflict_type = scene_plan.get("conflict_type", "")
                    emotion_type = scene_plan.get("emotion_type", "")

                    result = await script_service.generate_script(
                        plot_context=f"{scene_desc}",
                        required_conflict=conflict_type,
                        required_emotion=emotion_type,
                        characters=scene_characters,
                        scene=scene_desc,
                        style=request.style,
                        length=request.length,
                        innovation_degree=request.innovation_degree
                    )

                    generated_scenes.append({
                        "scene_number": scene_plan.get("scene_number", 0),
                        "scene_description": scene_desc,
                        "script": result["generated_script"],
                        "confidence": result.get("confidence", 0.85)
                    })

                except Exception as e:
                    logger.error(f"Failed to generate scene {scene_plan.get('scene_number')}: {str(e)}")
                    generated_scenes.append({
                        "scene_number": scene_plan.get("scene_number", 0),
                        "scene_description": scene_plan.get("scene_description", ""),
                        "script": f"生成失败: {str(e)}",
                        "confidence": 0.0
                    })

        generation_time = time.time() - start_time

        await StoryPlanCRUD.update(db, request.plan_id, status="completed")

        return GenerateFullScriptResponse(
            plan_id=request.plan_id,
            generated_scenes=generated_scenes,
            total_scene_count=len(generated_scenes),
            generation_time_seconds=generation_time
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to generate full script: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to generate full script: {str(e)}")


@router.post("/plan-story", response_model=SaveStoryPlanResponse)
async def save_story_plan(request: SaveStoryPlanRequest, db: AsyncSession = Depends(get_db)):
    """保存剧情规划到数据库"""
    try:
        logger.info(f"Saving story plan: {request.title}")
        
        phases_data = [phase.dict() for phase in request.phases_data]
        
        plan = await StoryPlanCRUD.create(
            db=db,
            title=request.title,
            story_outline=request.story_outline,
            characters=request.characters,
            structure_type=request.structure_type,
            phases_data=phases_data,
            total_scene_count=request.total_scene_count,
            status=request.status
        )
        
        return SaveStoryPlanResponse(
            id=str(plan.id),
            title=plan.title,
            story_outline=plan.story_outline,
            characters=plan.characters,
            structure_type=plan.structure_type,
            phases_data=plan.phases_data,
            total_scene_count=plan.total_scene_count,
            status=plan.status,
            created_at=plan.created_at.isoformat(),
            updated_at=plan.updated_at.isoformat()
        )
    except Exception as e:
        logger.error(f"Failed to save story plan: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to save story plan: {str(e)}")


@router.get("/plan/{plan_id}", response_model=SaveStoryPlanResponse)
async def get_story_plan(plan_id: str, db: AsyncSession = Depends(get_db)):
    """获取剧情规划详情"""
    try:
        plan = await StoryPlanCRUD.get_by_id(db=db, plan_id=plan_id)
        if not plan:
            raise HTTPException(status_code=404, detail="Story plan not found")
        
        return SaveStoryPlanResponse(
            id=str(plan.id),
            title=plan.title,
            story_outline=plan.story_outline,
            characters=plan.characters,
            structure_type=plan.structure_type,
            phases_data=plan.phases_data,
            total_scene_count=plan.total_scene_count,
            status=plan.status,
            created_at=plan.created_at.isoformat(),
            updated_at=plan.updated_at.isoformat()
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get story plan: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to get story plan: {str(e)}")


@router.put("/plan/{plan_id}", response_model=UpdateStoryPlanResponse)
async def update_story_plan(plan_id: str, request: UpdateStoryPlanRequest, db: AsyncSession = Depends(get_db)):
    """编辑剧情规划"""
    try:
        existing_plan = await StoryPlanCRUD.get_by_id(db=db, plan_id=plan_id)
        if not existing_plan:
            raise HTTPException(status_code=404, detail="Story plan not found")
        
        update_data = {}
        if request.title is not None:
            update_data["title"] = request.title
        if request.story_outline is not None:
            update_data["story_outline"] = request.story_outline
        if request.characters is not None:
            update_data["characters"] = request.characters
        if request.structure_type is not None:
            update_data["structure_type"] = request.structure_type
        if request.phases_data is not None:
            update_data["phases_data"] = [phase.dict() for phase in request.phases_data]
        if request.total_scene_count is not None:
            update_data["total_scene_count"] = request.total_scene_count
        if request.status is not None:
            update_data["status"] = request.status
        
        updated_plan = await StoryPlanCRUD.update(db=db, plan_id=plan_id, **update_data)
        
        return UpdateStoryPlanResponse(
            id=str(updated_plan.id),
            title=updated_plan.title,
            story_outline=updated_plan.story_outline,
            characters=updated_plan.characters,
            structure_type=updated_plan.structure_type,
            phases_data=updated_plan.phases_data,
            total_scene_count=updated_plan.total_scene_count,
            status=updated_plan.status,
            updated_at=updated_plan.updated_at.isoformat()
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to update story plan: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to update story plan: {str(e)}")


@router.get("/plan", response_model=StoryPlanListResponse)
async def list_story_plans(
    skip: int = 0,
    limit: int = 20,
    status: Optional[str] = None,
    db: AsyncSession = Depends(get_db)
):
    """获取剧情规划列表"""
    try:
        plans, total = await StoryPlanCRUD.list(db=db, skip=skip, limit=limit, status=status)
        
        plan_items = [
            SaveStoryPlanResponse(
                id=str(plan.id),
                title=plan.title,
                story_outline=plan.story_outline,
                characters=plan.characters,
                structure_type=plan.structure_type,
                phases_data=plan.phases_data,
                total_scene_count=plan.total_scene_count,
                status=plan.status,
                created_at=plan.created_at.isoformat(),
                updated_at=plan.updated_at.isoformat()
            )
            for plan in plans
        ]
        
        return StoryPlanListResponse(
            items=plan_items,
            total=total,
            skip=skip,
            limit=limit
        )
    except Exception as e:
        logger.error(f"Failed to list story plans: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to list story plans: {str(e)}")


@router.delete("/plan/{plan_id}")
async def delete_story_plan(plan_id: str, db: AsyncSession = Depends(get_db)):
    """删除剧情规划"""
    try:
        existing_plan = await StoryPlanCRUD.get_by_id(db=db, plan_id=plan_id)
        if not existing_plan:
            raise HTTPException(status_code=404, detail="Story plan not found")
        
        await StoryPlanCRUD.delete(db=db, plan_id=plan_id)
        return {"message": "Story plan deleted successfully"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to delete story plan: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to delete story plan: {str(e)}")