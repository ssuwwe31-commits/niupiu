from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from app.api.script import router as script_router
from app.api.novel import router as novel_router
from app.api.character import router as character_router
from app.api.observability import router as observability_router
from app.api.rag import router as rag_router
from app.api.story_plan import router as story_plan_router
from app.api.quality_evaluation import router as quality_evaluation_router
from app.config import get_settings
import logging

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
    handlers=[logging.StreamHandler()]
)

settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    from app.db.database import init_db
    from app.services.ollama_client import get_ollama_manager
    from app.services.rag_service import _update_settings, rag_service
    from app.services.observability_service import initialize_observability
    
    await init_db()
    
    ollama_manager = get_ollama_manager()
    ollama_manager.initialize()
    
    _update_settings()
    
    await rag_service.initialize_vector_store()
    
    initialize_observability()
    
    yield
    
    ollama_manager.close()


app = FastAPI(
    title="AI漫剧剧本生成系统",
    description="基于RAG的AI漫剧剧本生成系统",
    version="1.0.0",
    lifespan=lifespan
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000", "http://localhost:5174"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(script_router)
app.include_router(novel_router)
app.include_router(character_router)
app.include_router(observability_router)
app.include_router(rag_router)
app.include_router(story_plan_router)
app.include_router(quality_evaluation_router)


@app.get("/")
async def root():
    return {
        "message": "AI漫剧剧本生成系统 API",
        "version": "1.0.0",
        "docs": "/docs"
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
