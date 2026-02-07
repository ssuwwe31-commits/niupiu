from typing import Any, List, Optional
from llama_index.core.llms import CustomLLM, CompletionResponse, LLMMetadata
from llama_index.core.llms.callbacks import llm_completion_callback
from llama_index.core.embeddings import BaseEmbedding
from llama_index.core.bridge.pydantic import PrivateAttr
import requests
import logging
import time

logger = logging.getLogger(__name__)


class RequestsOllamaLLM(CustomLLM):
    context_window: int = 8192
    num_output: int = 2048
    model_name: str = "qwen3:30b"
    base_url: str = "http://localhost:11434"
    temperature: float = 0.7
    top_p: float = 0.9
    request_timeout: float = 120.0
    repeat_penalty: float = 1.1
    _session: Optional[requests.Session] = PrivateAttr(default=None)

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        if "session" in kwargs:
            self._session = kwargs["session"]
        else:
            self._session = requests.Session()

    @property
    def metadata(self) -> LLMMetadata:
        return LLMMetadata(
            context_window=self.context_window,
            num_output=self.num_output,
            model_name=self.model_name,
        )

    @llm_completion_callback()
    def complete(self, prompt: str, **kwargs: Any) -> CompletionResponse:
        start_time = time.time()
        try:
            url = f"{self.base_url}/api/generate"
            data = {
                "model": self.model_name,
                "prompt": prompt,
                "stream": False,
                "options": {
                    "temperature": self.temperature,
                    "top_p": self.top_p,
                    "num_predict": self.num_output,
                    "repeat_penalty": self.repeat_penalty,
                }
            }

            response = self._session.post(
                url,
                json=data,
                timeout=self.request_timeout,
                headers={"Content-Type": "application/json"}
            )
            response.raise_for_status()
            result = response.json()
            response_text = result.get("response", "")
            
            latency_ms = (time.time() - start_time) * 1000
            
            try:
                from app.services.observability_service import log_llm_call
                log_llm_call(
                    model=self.model_name,
                    input_text=prompt,
                    output_text=response_text,
                    input_tokens=result.get("prompt_eval_count", 0),
                    output_tokens=result.get("eval_count", 0),
                    latency_ms=latency_ms,
                    metadata={"provider": "ollama", "base_url": self.base_url}
                )
            except ImportError:
                pass
            
            return CompletionResponse(text=response_text)
        except Exception as e:
            logger.error(f"Error in RequestsOllamaLLM.complete: {e}")
            raise

    @llm_completion_callback()
    def stream_complete(self, prompt: str, **kwargs: Any):
        try:
            url = f"{self.base_url}/api/generate"
            data = {
                "model": self.model_name,
                "prompt": prompt,
                "stream": True,
                "options": {
                    "temperature": self.temperature,
                    "top_p": self.top_p,
                    "num_predict": self.num_output,
                    "repeat_penalty": self.repeat_penalty,
                }
            }

            response = self._session.post(
                url,
                json=data,
                stream=True,
                timeout=self.request_timeout,
                headers={"Content-Type": "application/json"}
            )
            response.raise_for_status()

            for line in response.iter_lines():
                if line:
                    import json
                    try:
                        chunk = json.loads(line)
                        if "response" in chunk:
                            yield CompletionResponse(text=chunk["response"], delta=chunk["response"])
                    except json.JSONDecodeError:
                        continue
        except Exception as e:
            logger.error(f"Error in RequestsOllamaLLM.stream_complete: {e}")
            raise

    def close(self):
        self.close_shared_session()

    def close_shared_session(self):
        self._session = None


class RequestsOllamaEmbedding(BaseEmbedding):
    embed_batch_size: int = 10
    model_name: str = "nomic-embed-text"
    base_url: str = "http://localhost:11434"
    timeout: float = 120.0
    _session: Optional[requests.Session] = PrivateAttr(default=None)

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        if "session" in kwargs:
            self._session = kwargs["session"]
        else:
            self._session = requests.Session()

    @property
    def _get_query_embedding(self):
        return self._get_embedding

    @property
    def _get_text_embedding(self):
        return self._get_embedding

    @property
    def _get_text_embeddings(self):
        return self._get_embeddings

    @property
    def _aget_query_embedding(self):
        return self._aget_embedding

    @property
    def _aget_text_embedding(self):
        return self._aget_embedding

    def _get_embedding(self, text: str) -> List[float]:
        try:
            url = f"{self.base_url}/api/embed"
            data = {
                "model": self.model_name,
                "input": text
            }
            response = self._session.post(
                url,
                json=data,
                timeout=self.timeout,
                headers={"Content-Type": "application/json"}
            )
            response.raise_for_status()
            result = response.json()
            if "embedding" in result:
                return result["embedding"]
            elif "embeddings" in result and len(result["embeddings"]) > 0:
                return result["embeddings"][0]
            else:
                raise ValueError(f"No embedding found in response: {result}")
        except Exception as e:
            logger.error(f"Error in RequestsOllamaEmbedding._get_embedding: {e}")
            raise

    def _get_embeddings(self, texts: List[str]) -> List[List[float]]:
        try:
            url = f"{self.base_url}/api/embed"
            data = {
                "model": self.model_name,
                "input": texts
            }
            response = self._session.post(
                url,
                json=data,
                timeout=self.timeout,
                headers={"Content-Type": "application/json"}
            )
            response.raise_for_status()
            result = response.json()
            if "embeddings" in result:
                return result["embeddings"]
            elif "embedding" in result and len(texts) == 1:
                return [result["embedding"]]
            else:
                raise ValueError(f"No embeddings found in response: {result}")
        except Exception as e:
            logger.error(f"Error in RequestsOllamaEmbedding._get_embeddings: {e}")
            raise

    def get_text_embedding(self, text: str) -> List[float]:
        return self._get_embedding(text)

    def get_text_embeddings(self, texts: List[str]) -> List[List[float]]:
        return self._get_embeddings(texts)

    async def _aget_embedding(self, text: str) -> List[float]:
        return self._get_embedding(text)

    def close(self):
        self.close_shared_session()

    def close_shared_session(self):
        self._session = None
