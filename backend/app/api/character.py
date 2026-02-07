from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.db.database import get_db
from app.models.character import Character
from app.schemas.character import CharacterCreate, CharacterUpdate, CharacterResponse, EmotionUpdateRequest
from app.services.rag_service import rag_service
from typing import List, Optional
from datetime import datetime
import logging

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

router = APIRouter(prefix="/api", tags=["character"])


@router.post("/characters", response_model=CharacterResponse)
async def create_character(
    character: CharacterCreate,
    db: AsyncSession = Depends(get_db)
):
    from app.db.database import init_db
    await init_db()

    result = await db.execute(
        select(Character).where(Character.name == character.name)
    )
    existing = result.scalar_one_or_none()
    if existing:
        raise HTTPException(status_code=400, detail=f"Character with name '{character.name}' already exists")

    db_character = Character(**character.dict())
    db.add(db_character)
    await db.commit()
    await db.refresh(db_character)
    return db_character


@router.get("/characters", response_model=List[CharacterResponse])
async def list_characters(
    skip: int = 0,
    limit: int = 100,
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(
        select(Character).offset(skip).limit(limit)
    )
    characters = result.scalars().all()
    return characters


@router.get("/characters/list", response_model=List[CharacterResponse])
async def list_characters_v2(
    skip: int = Query(0, description="跳过数量"),
    limit: int = Query(100, description="返回数量"),
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(
        select(Character).offset(skip).limit(limit)
    )
    characters = result.scalars().all()
    return characters


@router.get("/characters/{character_id}", response_model=CharacterResponse)
async def get_character(character_id: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Character).where(Character.id == character_id))
    character = result.scalar_one_or_none()
    if not character:
        raise HTTPException(status_code=404, detail="Character not found")
    return character


@router.put("/characters/{character_id}", response_model=CharacterResponse)
async def update_character(
    character_id: str,
    character_update: CharacterUpdate,
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(select(Character).where(Character.id == character_id))
    character = result.scalar_one_or_none()
    if not character:
        raise HTTPException(status_code=404, detail="Character not found")
    
    update_data = character_update.dict(exclude_unset=True)
    for field, value in update_data.items():
        setattr(character, field, value)
    
    character.updated_at = datetime.now().isoformat()
    await db.commit()
    await db.refresh(character)
    return character


@router.delete("/characters/{character_id}")
async def delete_character(
    character_id: str,
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(select(Character).where(Character.id == character_id))
    character = result.scalar_one_or_none()
    if not character:
        raise HTTPException(status_code=404, detail="Character not found")
    
    await db.delete(character)
    await db.commit()
    return {"message": "Character deleted successfully", "character_id": character_id}


@router.post("/characters/{character_name}/emotion")
async def update_character_emotion(
    character_name: str,
    emotion_request: EmotionUpdateRequest
):
    try:
        result = await rag_service.update_character_emotion(
            character_name=character_name,
            emotion_type=emotion_request.emotion_type,
            intensity=emotion_request.intensity,
            decay_rate=emotion_request.decay_rate
        )
        return result
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal error: {str(e)}")


@router.post("/characters/decay-emotions")
async def decay_emotions(
    character_name: Optional[str] = Query(None, description="角色名称，不指定则衰减所有角色情绪"),
    time_offset_hours: float = Query(0.0, description="时间偏移（小时），用于测试，默认为0")
):
    try:
        logger.info(f"[API DECAY] Received request: character_name={character_name}, time_offset_hours={time_offset_hours}")
        result = await rag_service.decay_emotions(character_name=character_name, time_offset_hours=time_offset_hours)
        logger.info(f"[API DECAY] Result: decaying_count={result.get('decayed_count', 0)}")
        return result
    except Exception as e:
        logger.error(f"[API DECAY] Error: {e}")
        raise HTTPException(status_code=500, detail=f"Internal error: {str(e)}")
