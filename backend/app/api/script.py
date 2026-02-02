from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.db.database import get_db
from app.models.story_unit import StoryUnit
from app.models.character import Character
from app.schemas.story_unit import StoryUnitCreate, StoryUnitResponse, StoryUnitSearch
from app.schemas.character import ScriptGenerationRequest, ScriptGenerationResponse
from app.services.rag_service import rag_service
from typing import List

router = APIRouter(prefix="/api", tags=["script"])


@router.on_event("startup")
async def startup_event():
    await rag_service.initialize_vector_store()


@router.post("/story-units", response_model=StoryUnitResponse)
async def create_story_unit(
    story_unit: StoryUnitCreate,
    db: AsyncSession = Depends(get_db)
):
    from app.db.database import init_db
    await init_db()

    db_story_unit = StoryUnit(**story_unit.dict())
    db.add(db_story_unit)
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
    )
    return {"results": results}


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
        )
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/health")
async def health_check():
    return {"status": "healthy"}
