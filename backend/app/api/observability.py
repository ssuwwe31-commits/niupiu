from fastapi import APIRouter, HTTPException
from typing import Dict, Any
from app.services.observability_service import get_cost_stats
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/observability", tags=["Observability"])


@router.get("/health")
async def observability_health() -> Dict[str, Any]:
    try:
        from app.config import get_settings
        settings = get_settings()
        
        return {
            "status": "enabled" if settings.ENABLE_LANGFUSE else "disabled",
            "service": "langfuse",
            "version": "self-hosted",
            "host": settings.LANGFUSE_HOST
        }
    except Exception as e:
        logger.error(f"Failed to check observability health: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/cost-stats")
async def get_cost_statistics(days: int = 7) -> Dict[str, Any]:
    try:
        if days < 1 or days > 365:
            raise HTTPException(status_code=400, detail="days must be between 1 and 365")
        
        return get_cost_stats(days=days)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get cost stats: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/info")
async def observability_info() -> Dict[str, Any]:
    try:
        from app.config import get_settings
        from app.services.observability_service import MODEL_PRICING
        
        settings = get_settings()
        
        return {
            "enabled": settings.ENABLE_LANGFUSE,
            "host": settings.LANGFUSE_HOST,
            "public_key": settings.LANGFUSE_PUBLIC_KEY[:10] + "..." if settings.LANGFUSE_PUBLIC_KEY else "",
            "model_pricing": MODEL_PRICING
        }
    except Exception as e:
        logger.error(f"Failed to get observability info: {e}")
        raise HTTPException(status_code=500, detail=str(e))
