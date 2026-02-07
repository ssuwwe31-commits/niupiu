from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, delete, func
from sqlalchemy.dialects.postgresql import insert
from typing import List, Optional, Dict, Any
from datetime import datetime
import uuid

from app.models.story_plan import StoryPlan


class StoryPlanCRUD:
    """剧情规划 CRUD 操作"""

    @staticmethod
    async def create(
        db: AsyncSession,
        title: str,
        story_outline: str,
        characters: List[str],
        structure_type: str,
        phases_data: List[Dict[str, Any]],
        total_scene_count: int = 0,
        status: str = "draft"
    ) -> StoryPlan:
        """创建剧情规划"""
        plan_id = str(uuid.uuid4())
        now = datetime.utcnow()
        
        plan = StoryPlan(
            id=plan_id,
            title=title,
            story_outline=story_outline,
            characters=characters,
            structure_type=structure_type,
            phases_data=phases_data,
            total_scene_count=total_scene_count,
            status=status,
            created_at=now,
            updated_at=now
        )
        
        db.add(plan)
        await db.commit()
        await db.refresh(plan)
        
        return plan

    @staticmethod
    async def get_by_id(db: AsyncSession, plan_id: str) -> Optional[StoryPlan]:
        """根据 ID 获取剧情规划"""
        result = await db.execute(
            select(StoryPlan).where(StoryPlan.id == plan_id)
        )
        return result.scalar_one_or_none()

    @staticmethod
    async def list(
        db: AsyncSession,
        skip: int = 0,
        limit: int = 100,
        status: Optional[str] = None,
        structure_type: Optional[str] = None
    ) -> tuple[List[StoryPlan], int]:
        """获取剧情规划列表"""
        query = select(StoryPlan)
        
        if status:
            query = query.where(StoryPlan.status == status)
        if structure_type:
            query = query.where(StoryPlan.structure_type == structure_type)
        
        query = query.order_by(StoryPlan.created_at.desc())
        
        total_query = select(func.count()).select_from(query.subquery())
        total_result = await db.execute(total_query)
        total = total_result.scalar()
        
        result = await db.execute(
            query.offset(skip).limit(limit)
        )
        
        return list(result.scalars().all()), total

    @staticmethod
    async def update(
        db: AsyncSession,
        plan_id: str,
        title: Optional[str] = None,
        story_outline: Optional[str] = None,
        characters: Optional[List[str]] = None,
        structure_type: Optional[str] = None,
        phases_data: Optional[List[Dict[str, Any]]] = None,
        total_scene_count: Optional[int] = None,
        status: Optional[str] = None
    ) -> Optional[StoryPlan]:
        """更新剧情规划"""
        update_data = {}
        
        if title is not None:
            update_data["title"] = title
        if story_outline is not None:
            update_data["story_outline"] = story_outline
        if characters is not None:
            update_data["characters"] = characters
        if structure_type is not None:
            update_data["structure_type"] = structure_type
        if phases_data is not None:
            update_data["phases_data"] = phases_data
        if total_scene_count is not None:
            update_data["total_scene_count"] = total_scene_count
        if status is not None:
            update_data["status"] = status
        
        update_data["updated_at"] = datetime.utcnow()
        
        await db.execute(
            update(StoryPlan)
            .where(StoryPlan.id == plan_id)
            .values(**update_data)
        )
        await db.commit()
        
        return await StoryPlanCRUD.get_by_id(db, plan_id)

    @staticmethod
    async def update_scene(
        db: AsyncSession,
        plan_id: str,
        scene_number: int,
        scene_data: Dict[str, Any]
    ) -> Optional[StoryPlan]:
        """更新指定场次"""
        plan = await StoryPlanCRUD.get_by_id(db, plan_id)
        if not plan:
            return None
        
        phases_data = plan.phases_data
        if not phases_data:
            return None
        
        for phase in phases_data:
            for scene in phase.get("scenes", []):
                if scene.get("scene_number") == scene_number:
                    scene.update(scene_data)
                    break
        
        plan.phases_data = phases_data
        plan.updated_at = datetime.utcnow()
        
        await db.commit()
        await db.refresh(plan)
        
        return plan

    @staticmethod
    async def delete(db: AsyncSession, plan_id: str) -> bool:
        """删除剧情规划"""
        result = await db.execute(
            delete(StoryPlan).where(StoryPlan.id == plan_id)
        )
        await db.commit()
        return result.rowcount > 0

    @staticmethod
    async def get_scene_by_number(
        db: AsyncSession,
        plan_id: str,
        scene_number: int
    ) -> Optional[Dict[str, Any]]:
        """获取指定场次"""
        plan = await StoryPlanCRUD.get_by_id(db, plan_id)
        if not plan or not plan.phases_data:
            return None
        
        for phase in plan.phases_data:
            for scene in phase.get("scenes", []):
                if scene.get("scene_number") == scene_number:
                    return scene
        
        return None


story_plan_crud = StoryPlanCRUD()
