import requests
from typing import Optional, Dict, Any
from app.config import get_settings
from app.services.ollama_llm import RequestsOllamaLLM, RequestsOllamaEmbedding
from app.services.deepseek_client import RequestsDeepSeekLLM
from app.services.observability_service import create_trace
import logging

logger = logging.getLogger(__name__)

settings = get_settings()

TASK_MODEL_MAPPING = {
    "plot_decomposition": {
        "primary": "qwen30b",
        "fallback": None
    },
    "semantic_validation": {
        "primary": "qwen30b",
        "fallback": None
    },
    "script_generation": {
        "primary": "qwen30b",
        "fallback": "deepseek_v3_2"
    },
    "script_refinement": {
        "primary": "deepseek_v3_2",
        "fallback": "qwen30b"
    },
    "embedding": {
        "primary": "bge-m3",
        "fallback": None
    }
}


class OllamaClientManager:
    def __init__(self):
        self._llm: Optional[RequestsOllamaLLM] = None
        self._llm_long_timeout: Optional[RequestsOllamaLLM] = None
        self._embed_model: Optional[RequestsOllamaEmbedding] = None
        self._deepseek_llm: Optional[RequestsDeepSeekLLM] = None
        self._session: Optional[requests.Session] = None
        self._initialized = False

    def initialize(self):
        if self._initialized:
            return

        logger.info("Initializing Ollama client manager...")
        
        session = requests.Session()
        session.headers.update({
            'Content-Type': 'application/json',
            'User-Agent': 'ai-drama-backend/1.0'
        })
        
        self._session = session

        self._llm = RequestsOllamaLLM(
            model_name=settings.LLM_MODEL,
            base_url=settings.OLLAMA_BASE_URL,
            request_timeout=120,
            context_window=8192,
            num_output=2048,
            temperature=0.7,
            top_p=0.9,
            repeat_penalty=1.1,
            session=session
        )

        self._llm_long_timeout = RequestsOllamaLLM(
            model_name=settings.LLM_MODEL,
            base_url=settings.OLLAMA_BASE_URL,
            request_timeout=300,
            context_window=16384,
            num_output=4096,
            temperature=0.5,
            top_p=0.95,
            repeat_penalty=1.1,
            session=session
        )

        self._embed_model = RequestsOllamaEmbedding(
            model_name=settings.EMBEDDING_MODEL,
            base_url=settings.OLLAMA_BASE_URL,
            embed_batch_size=10,
            timeout=120,
            session=session
        )

        if settings.ENABLE_DEEPSEEK and settings.DEEPSEEK_API_KEY:
            logger.info("Initializing DeepSeek client...")
            self._deepseek_llm = RequestsDeepSeekLLM(
                model_name=settings.DEEPSEEK_MODEL,
                api_key=settings.DEEPSEEK_API_KEY,
                base_url=settings.DEEPSEEK_BASE_URL,
                temperature=0.7,
                top_p=0.95,
                max_tokens=4096,
                request_timeout=120,
                session=session
            )
            logger.info("DeepSeek client initialized successfully")
        else:
            logger.info("DeepSeek client disabled or not configured")

        self._initialized = True
        logger.info("Ollama client manager initialized successfully")

    def close(self):
        if not self._initialized:
            return

        logger.info("Closing Ollama client manager...")

        if self._llm:
            self._llm.close_shared_session()

        if self._llm_long_timeout:
            self._llm_long_timeout.close_shared_session()

        if self._embed_model:
            self._embed_model.close_shared_session()

        if self._deepseek_llm:
            self._deepseek_llm.close()

        if self._session:
            self._session.close()
            self._session = None

        self._llm = None
        self._llm_long_timeout = None
        self._embed_model = None
        self._deepseek_llm = None
        self._initialized = False
        logger.info("Ollama client manager closed successfully")

    @property
    def llm(self) -> RequestsOllamaLLM:
        if not self._initialized:
            raise RuntimeError("Ollama client manager not initialized. Call initialize() first.")
        return self._llm

    @property
    def llm_long_timeout(self) -> RequestsOllamaLLM:
        if not self._initialized:
            raise RuntimeError("Ollama client manager not initialized. Call initialize() first.")
        return self._llm_long_timeout

    @property
    def embed_model(self) -> RequestsOllamaEmbedding:
        if not self._initialized:
            raise RuntimeError("Ollama client manager not initialized. Call initialize() first.")
        return self._embed_model

    @property
    def deepseek_llm(self) -> Optional[RequestsDeepSeekLLM]:
        if not self._initialized:
            raise RuntimeError("Ollama client manager not initialized. Call initialize() first.")
        return self._deepseek_llm

    def get_model_for_task(self, task_type: str, use_fallback: bool = True, task_metadata: Optional[Dict[str, Any]] = None) -> Any:
        """
        根据任务类型获取合适的模型
        
        Args:
            task_type: 任务类型，如 'plot_decomposition', 'script_generation' 等
            use_fallback: 当主模型不可用时是否使用备用模型
            task_metadata: 任务元数据，用于可观测性追踪
        
        Returns:
            对应的模型实例
        """
        if task_type not in TASK_MODEL_MAPPING:
            logger.warning(f"Unknown task type: {task_type}, falling back to default LLM")
            return self.llm

        config = TASK_MODEL_MAPPING[task_type]
        primary = config["primary"]
        fallback = config.get("fallback")

        trace = create_trace(f"task_{task_type}", {
            "task_type": task_type,
            "primary_model": primary,
            "fallback_model": fallback,
            "use_fallback": use_fallback,
            **(task_metadata or {})
        })

        if primary == "qwen30b":
            return self.llm
        elif primary == "deepseek_v3_2":
            if self._deepseek_llm and settings.ENABLE_DEEPSEEK:
                return self._deepseek_llm
            elif use_fallback and fallback == "qwen30b":
                logger.warning(f"DeepSeek not available for task {task_type}, falling back to qwen30b")
                return self.llm
            else:
                logger.warning(f"DeepSeek not available for task {task_type}, using qwen30b as default")
                return self.llm
        elif primary == "bge-m3":
            return self._embed_model
        else:
            logger.warning(f"Unknown primary model: {primary}, falling back to default LLM")
            return self.llm

    def should_use_deepseek(self, current_score: Optional[float] = None) -> bool:
        """
        判断是否应该使用 deepseek 模型
        
        Args:
            current_score: 当前 qwen30b 的评分（如果有）
        
        Returns:
            True 表示应该使用 deepseek，False 表示继续使用 qwen30b
        """
        if not settings.ENABLE_DEEPSEEK or not self._deepseek_llm:
            return False
        
        if current_score is not None and current_score >= 3.5:
            return False
        
        return True


_ollama_manager = OllamaClientManager()


def get_ollama_manager() -> OllamaClientManager:
    return _ollama_manager
