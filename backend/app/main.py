from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api.script import router as script_router
from app.config import get_settings

settings = get_settings()

app = FastAPI(
    title="AI漫剧剧本生成系统",
    description="基于RAG的AI漫剧剧本生成系统",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(script_router)


@app.get("/")
async def root():
    return {
        "message": "AI漫剧剧本生成系统 API",
        "version": "1.0.0",
        "docs": "/docs"
    }


@app.on_event("startup")
async def startup_event():
    from app.db.database import init_db
    await init_db()


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
