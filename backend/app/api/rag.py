from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
from app.db.database import get_db
from pydantic import BaseModel

router = APIRouter(prefix="/api/rag", tags=["rag"])


class SearchRequest(BaseModel):
    query: str
    top_k: int = 5


@router.post("/search-story-units")
async def search_story_units(
    request: SearchRequest,
    db: AsyncSession = Depends(get_db)
):
    from app.services.rag_service import rag_service

    results = await rag_service.search_story_units(
        query=request.query,
        top_k=request.top_k
    )

    return results
