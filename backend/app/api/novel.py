from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.db.database import get_db
from app.models.novel import Novel
from app.schemas.novel import NovelCreate, NovelResponse, NovelDecomposeRequest, NovelDecomposeResponse
from app.services.novel_service import novel_service
from typing import List

router = APIRouter(prefix="/api/novels", tags=["novels"])


@router.post("/upload", response_model=NovelResponse)
async def upload_novel(
    file: UploadFile = File(...),
    title: str = Form(...),
    author: str = Form(default=None),
    summary: str = Form(default=None),
    db: AsyncSession = Depends(get_db)
):
    from app.db.database import init_db
    await init_db()

    try:
        content = await file.read()
        file_size = len(content)
        file_type = file.filename.split('.')[-1].lower()

        file_path = await novel_service.save_uploaded_file(content, file.filename)

        novel_data = NovelCreate(
            title=title,
            author=author,
            file_type=file_type,
            file_size=file_size,
            summary=summary
        )

        db_novel = Novel(
            title=novel_data.title,
            author=novel_data.author,
            file_path=file_path,
            file_type=novel_data.file_type,
            file_size=novel_data.file_size,
            summary=novel_data.summary
        )

        db.add(db_novel)
        await db.commit()
        await db.refresh(db_novel)
        return db_novel

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"上传失败: {str(e)}")


@router.get("", response_model=List[NovelResponse])
async def list_novels(
    skip: int = 0,
    limit: int = 100,
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(select(Novel).offset(skip).limit(limit))
    novels = result.scalars().all()
    return novels


@router.get("/{novel_id}", response_model=NovelResponse)
async def get_novel(novel_id: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Novel).where(Novel.id == novel_id))
    novel = result.scalar_one_or_none()
    if not novel:
        raise HTTPException(status_code=404, detail="小说不存在")
    return novel


@router.post("/{novel_id}/decompose", response_model=NovelDecomposeResponse)
async def decompose_novel(
    novel_id: str,
    request: NovelDecomposeRequest,
    db: AsyncSession = Depends(get_db)
):
    result = await novel_service.decompose_novel(novel_id, request.chapter_range)

    if "error" in result:
        raise HTTPException(status_code=400, detail=result["error"])

    if result["units"]:
        from app.models.story_unit import StoryUnit
        from app.db.database import init_db
        from app.services.ollama_client import get_ollama_manager

        await init_db()
        ollama_manager = get_ollama_manager()
        embed_model = ollama_manager.embed_model

        for unit_data in result["units"]:
            db_unit = StoryUnit(**unit_data)
            db.add(db_unit)

        await db.commit()

        for unit_data in result["units"]:
            stmt = select(StoryUnit).where(StoryUnit.original_text == unit_data["original_text"])
            result_stmt = await db.execute(stmt)
            db_unit = result_stmt.scalar_one_or_none()
            if db_unit and db_unit.embedding is None:
                text = f"{db_unit.scene} {db_unit.core_conflict} {db_unit.original_text}"
                embedding = embed_model.get_text_embedding(text)
                db_unit.embedding = embedding

        await db.commit()

    return NovelDecomposeResponse(
        novel_id=result["novel_id"],
        total_units=result["total_units"],
        success_count=result["success_count"],
        failed_count=result["failed_count"],
        message=result["message"]
    )


@router.delete("/{novel_id}")
async def delete_novel(novel_id: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Novel).where(Novel.id == novel_id))
    novel = result.scalar_one_or_none()
    if not novel:
        raise HTTPException(status_code=404, detail="小说不存在")

    try:
        from pathlib import Path
        file_path = Path(novel.file_path)
        if file_path.exists():
            file_path.unlink()
    except Exception:
        pass

    await db.delete(novel)
    await db.commit()
    return {"message": "删除成功"}
