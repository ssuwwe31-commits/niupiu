from typing import Any, Dict, Optional
from datetime import datetime, timedelta
import time
import logging

from app.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()

_observability_initialized = False
_langfuse_handler = None

MODEL_PRICING = {
    "deepseek-chat": {
        "input_price": 0.0000014,
        "output_price": 0.0000028
    },
    "deepseek-v3.2": {
        "input_price": 0.0000014,
        "output_price": 0.0000028
    },
    "qwen3:30b": {
        "input_price": 0,
        "output_price": 0
    },
    "qwen3": {
        "input_price": 0,
        "output_price": 0
    }
}


def initialize_observability():
    global _observability_initialized, _langfuse_handler
    if _observability_initialized:
        return
    if not settings.ENABLE_LANGFUSE:
        logger.info("Langfuse observability disabled")
        _observability_initialized = True
        return
    try:
        from langfuse import get_client
        import logging
        import os
        
        logging.getLogger("langfuse").setLevel(logging.DEBUG)
        
        os.environ["LANGFUSE_BASE_URL"] = settings.LANGFUSE_BASE_URL
        os.environ["LANGFUSE_PUBLIC_KEY"] = settings.LANGFUSE_PUBLIC_KEY
        os.environ["LANGFUSE_SECRET_KEY"] = settings.LANGFUSE_SECRET_KEY
        
        langfuse = get_client()
        _langfuse_handler = langfuse
        logger.info(f"Langfuse observability initialized: {settings.LANGFUSE_BASE_URL}, public_key: {settings.LANGFUSE_PUBLIC_KEY[:10]}...")
        _observability_initialized = True
    except ImportError:
        logger.warning("langfuse package not installed. Install with: pip install langfuse")
        _observability_initialized = True
    except Exception as e:
        logger.warning(f"Langfuse initialization failed: {e}")
        _observability_initialized = True


def log_llm_call(
    model: str,
    input_text: str,
    output_text: str,
    input_tokens: Optional[int] = None,
    output_tokens: Optional[int] = None,
    total_tokens: Optional[int] = None,
    latency_ms: Optional[float] = None,
    metadata: Optional[Dict[str, Any]] = None
) -> None:
    if not settings.ENABLE_LANGFUSE:
        logger.debug(f"Langfuse disabled, skipping LLM call logging for {model}")
        return
    
    if not _langfuse_handler:
        logger.debug(f"Langfuse handler not initialized, skipping LLM call logging for {model}")
        return
    
    try:
        pricing = MODEL_PRICING.get(model, MODEL_PRICING.get(model.split(":")[0], {"input_price": 0, "output_price": 0}))
        cost = 0.0
        
        if input_tokens and output_tokens:
            cost = (input_tokens * pricing["input_price"] / 1000000 +
                    output_tokens * pricing["output_price"] / 1000000)
        
        tokens = total_tokens or (input_tokens + output_tokens if input_tokens and output_tokens else 0)
        
        try:
            with _langfuse_handler.start_as_current_observation(
                as_type="generation",
                name="llm_generation",
                model=model
            ) as generation:
                generation.update(
                    input=input_text,
                    output=output_text,
                    usage={
                        "input": input_tokens or 0,
                        "output": output_tokens or 0,
                        "total": tokens
                    },
                    cost={
                        "input": input_tokens * pricing["input_price"] / 1000000 if input_tokens else 0,
                        "output": output_tokens * pricing["output_price"] / 1000000 if output_tokens else 0,
                        "total": cost
                    },
                    metadata={
                        "latency_ms": latency_ms,
                        **(metadata or {})
                    }
                )
            
            _langfuse_handler.flush()
        except Exception as obs_error:
            logger.warning(f"Failed to create observation: {obs_error}")
        
        logger.info(
            f"LLM call - Model: {model}, "
            f"Tokens: {tokens}, "
            f"Cost: ${cost:.6f}, "
            f"Latency: {latency_ms:.0f}ms" if latency_ms else f"Model: {model}, Tokens: {tokens}, Cost: ${cost:.6f}"
        )
    except Exception as e:
        logger.error(f"Failed to log LLM call: {e}")


def create_trace(name: str, metadata: Optional[Dict[str, Any]] = None) -> Optional[Any]:
    if not settings.ENABLE_LANGFUSE:
        return None
    
    try:
        from langfuse import get_client
        langfuse = get_client()
        return langfuse.start_as_current_observation(as_type="span", name=name)
    except Exception as e:
        logger.error(f"Failed to create trace: {e}")
        return None


def get_cost_stats(days: int = 7) -> Dict[str, Any]:
    if not settings.ENABLE_LANGFUSE:
        return {"enabled": False, "message": "Langfuse is disabled"}
    
    try:
        from langfuse import get_client
        langfuse = get_client()
        
        start_date = datetime.now() - timedelta(days=days)
        
        try:
            observations = langfuse.api.observations_v2.get_many(
                type="GENERATION",
                from_timestamp=start_date,
                to_timestamp=datetime.now(),
                limit=100
            )
            
            total_cost = 0.0
            total_tokens = 0
            model_breakdown = {}
            
            if observations and hasattr(observations, 'data'):
                for obs in observations.data:
                    model = getattr(obs, 'provided_model_name', None) or getattr(obs, 'model', None) or "unknown"
                    
                    input_tokens = getattr(obs, 'usage_input_tokens', 0) or 0
                    output_tokens = getattr(obs, 'usage_output_tokens', 0) or 0
                    event_tokens = input_tokens + output_tokens
                    
                    pricing = MODEL_PRICING.get(model, MODEL_PRICING.get(model.split(":")[0], {"input_price": 0, "output_price": 0}))
                    event_cost = (input_tokens * pricing["input_price"] / 1000000 +
                                 output_tokens * pricing["output_price"] / 1000000)
                    
                    total_cost += event_cost
                    total_tokens += event_tokens
                    
                    if model not in model_breakdown:
                        model_breakdown[model] = {
                            "tokens": 0,
                            "cost": 0.0,
                            "calls": 0
                        }
                    model_breakdown[model]["tokens"] += event_tokens
                    model_breakdown[model]["cost"] += event_cost
                    model_breakdown[model]["calls"] += 1
            
            return {
                "enabled": True,
                "period_days": days,
                "start_date": start_date.isoformat(),
                "end_date": datetime.now().isoformat(),
                "total_cost_usd": round(total_cost, 6),
                "total_tokens": total_tokens,
                "model_breakdown": {
                    model: {
                        "tokens": data["tokens"],
                        "cost_usd": round(data["cost"], 6),
                        "calls": data["calls"]
                    }
                    for model, data in model_breakdown.items()
                }
            }
        except Exception as e:
            logger.warning(f"Failed to fetch observations from Langfuse: {e}")
            return {
                "enabled": True,
                "period_days": days,
                "total_cost_usd": 0.0,
                "total_tokens": 0,
                "model_breakdown": {},
                "message": "Could not fetch detailed stats, check Langfuse connection"
            }
    except Exception as e:
        logger.error(f"Failed to get cost stats: {e}")
        return {"enabled": True, "error": str(e)}
