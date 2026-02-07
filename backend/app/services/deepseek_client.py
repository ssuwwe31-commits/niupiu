from typing import Any, Optional
from llama_index.core.llms import CustomLLM, CompletionResponse, LLMMetadata
from llama_index.core.llms.callbacks import llm_completion_callback
from llama_index.core.bridge.pydantic import PrivateAttr
import requests
import logging
import time
import json
import asyncio
import aiohttp

logger = logging.getLogger(__name__)


class RequestsDeepSeekLLM(CustomLLM):
    context_window: int = 131072
    num_output: int = 8192
    model_name: str = "deepseek-chat"
    api_key: str = ""
    base_url: str = "https://api.deepseek.com/v1"
    temperature: float = 0.7
    top_p: float = 0.95
    max_tokens: int = 8192
    request_timeout: float = 300.0
    _session: Optional[requests.Session] = PrivateAttr(default=None)

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        if "session" in kwargs:
            self._session = kwargs["session"]
        else:
            self._session = requests.Session()

        if "reasoner" in self.model_name.lower():
            self.context_window = 131072
            self.num_output = 32768
            self.max_tokens = 32768
            self.request_timeout = 600.0

    @property
    def metadata(self) -> LLMMetadata:
        return LLMMetadata(
            context_window=self.context_window,
            num_output=self.num_output,
            model_name=self.model_name,
        )

    @llm_completion_callback()
    def complete(self, prompt: str, **kwargs: Any) -> CompletionResponse:
        try:
            start_time = time.time()
            
            url = f"{self.base_url}/chat/completions"
            headers = {
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self.api_key}"
            }
            data = {
                "model": self.model_name,
                "messages": [
                    {"role": "user", "content": prompt}
                ],
                "temperature": self.temperature,
                "top_p": self.top_p,
                "max_tokens": self.max_tokens,
                "stream": True
            }

            logger.info(f"DeepSeek API request: URL={url}, model={self.model_name}, timeout={self.request_timeout}s")

            response = self._session.post(
                url,
                json=data,
                stream=True,
                timeout=self.request_timeout,
                headers=headers
            )
            response.raise_for_status()
            
            logger.info(f"DeepSeek API response status: {response.status_code}")
            
            full_content = ""
            input_tokens = 0
            output_tokens = 0
            chunk_count = 0
            
            for line in response.iter_lines():
                if line:
                    chunk_count += 1
                    if chunk_count % 10 == 0:
                        logger.info(f"Processing chunk {chunk_count}...")
                    try:
                        if line.startswith(b"data: "):
                            line = line[6:]
                        if line.strip() == b"[DONE]":
                            logger.info(f"Received [DONE] signal after {chunk_count} chunks")
                            break
                        chunk = json.loads(line)
                        if "choices" in chunk and len(chunk["choices"]) > 0:
                            delta = chunk["choices"][0].get("delta", {})
                            content = delta.get("content")
                            if content is not None:
                                full_content += content
                            
                            if "usage" in chunk:
                                usage = chunk["usage"]
                                input_tokens = usage.get("prompt_tokens", 0)
                                output_tokens = usage.get("completion_tokens", 0)
                    except (json.JSONDecodeError, KeyError) as e:
                        logger.warning(f"Failed to parse chunk {chunk_count}: {e}")
                        continue
            
            logger.info(f"DeepSeek API streaming completed: {chunk_count} chunks, content length: {len(full_content)}")
            
            total_tokens = input_tokens + output_tokens
            
            logger.info(f"DeepSeek API call: input={input_tokens} tokens, output={output_tokens} tokens, total={total_tokens} tokens")

            latency_ms = (time.time() - start_time) * 1000

            try:
                from app.services.observability_service import log_llm_call
                log_llm_call(
                    model=self.model_name,
                    input_text=prompt,
                    output_text=full_content,
                    input_tokens=input_tokens,
                    output_tokens=output_tokens,
                    latency_ms=latency_ms,
                    metadata={"provider": "deepseek", "base_url": self.base_url, "stream": True}
                )
            except ImportError:
                pass

            return CompletionResponse(
                text=full_content,
                raw={"usage": {"prompt_tokens": input_tokens, "completion_tokens": output_tokens, "total_tokens": total_tokens}}
            )
        except Exception as e:
            logger.error(f"Error in RequestsDeepSeekLLM.complete: {e}")
            raise

    @llm_completion_callback()
    async def acomplete(self, prompt: str, **kwargs: Any) -> CompletionResponse:
        try:
            start_time = time.time()

            url = f"{self.base_url}/chat/completions"
            headers = {
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self.api_key}"
            }
            data = {
                "model": self.model_name,
                "messages": [
                    {"role": "user", "content": prompt}
                ],
                "temperature": self.temperature,
                "top_p": self.top_p,
                "max_tokens": self.max_tokens,
                "stream": True
            }

            logger.info(f"DeepSeek API async request: URL={url}, model={self.model_name}, timeout={self.request_timeout}s")

            async with aiohttp.ClientSession() as session:
                async with session.post(
                    url,
                    json=data,
                    timeout=aiohttp.ClientTimeout(total=self.request_timeout),
                    headers=headers
                ) as response:
                    response.raise_for_status()

                    logger.info(f"DeepSeek API async response status: {response.status}")

                    full_content = ""
                    input_tokens = 0
                    output_tokens = 0
                    chunk_count = 0

                    while True:
                        line = await response.content.readline()
                        if not line:
                            break
                        chunk_count += 1
                        if chunk_count % 10 == 0:
                            logger.info(f"Processing chunk {chunk_count}...")
                        try:
                            line_str = line.decode('utf-8').strip()
                            if line_str.startswith("data: "):
                                line_str = line_str[6:]
                            if line_str == "[DONE]":
                                logger.info(f"Received [DONE] signal after {chunk_count} chunks")
                                break
                            if not line_str:
                                continue
                            chunk = json.loads(line_str)
                            if "choices" in chunk and len(chunk["choices"]) > 0:
                                delta = chunk["choices"][0].get("delta", {})
                                content = delta.get("content")
                                if content is not None:
                                    full_content += content

                                if "usage" in chunk:
                                    usage = chunk["usage"]
                                    input_tokens = usage.get("prompt_tokens", 0)
                                    output_tokens = usage.get("completion_tokens", 0)
                        except (json.JSONDecodeError, KeyError, UnicodeDecodeError) as e:
                            logger.warning(f"Failed to parse chunk {chunk_count}: {e}")
                            continue

                    logger.info(f"DeepSeek API async streaming completed: {chunk_count} chunks, content length: {len(full_content)}")

                    total_tokens = input_tokens + output_tokens

                    logger.info(f"DeepSeek API async call: input={input_tokens} tokens, output={output_tokens} tokens, total={total_tokens} tokens")

                    latency_ms = (time.time() - start_time) * 1000

                    try:
                        from app.services.observability_service import log_llm_call
                        log_llm_call(
                            model=self.model_name,
                            input_text=prompt,
                            output_text=full_content,
                            input_tokens=input_tokens,
                            output_tokens=output_tokens,
                            latency_ms=latency_ms,
                            metadata={"provider": "deepseek", "base_url": self.base_url, "stream": True}
                        )
                    except ImportError:
                        pass

                    return CompletionResponse(
                        text=full_content,
                        raw={"usage": {"prompt_tokens": input_tokens, "completion_tokens": output_tokens, "total_tokens": total_tokens}}
                    )
        except Exception as e:
            logger.error(f"Error in RequestsDeepSeekLLM.acomplete: {e}")
            raise

    @llm_completion_callback()
    def stream_complete(self, prompt: str, **kwargs: Any):
        try:
            url = f"{self.base_url}/chat/completions"
            headers = {
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self.api_key}"
            }
            data = {
                "model": self.model_name,
                "messages": [
                    {"role": "user", "content": prompt}
                ],
                "temperature": self.temperature,
                "top_p": self.top_p,
                "max_tokens": self.max_tokens,
                "stream": True
            }

            response = self._session.post(
                url,
                json=data,
                stream=True,
                timeout=self.request_timeout,
                headers=headers
            )
            response.raise_for_status()

            for line in response.iter_lines():
                if line:
                    try:
                        if line.startswith(b"data: "):
                            line = line[6:]
                        if line.strip() == b"[DONE]":
                            break
                        chunk = json.loads(line)
                        if "choices" in chunk and len(chunk["choices"]) > 0:
                            delta = chunk["choices"][0].get("delta", {})
                            content = delta.get("content", "")
                            if content:
                                yield CompletionResponse(text=content, delta=content)
                    except (json.JSONDecodeError, KeyError):
                        continue
        except Exception as e:
            logger.error(f"Error in RequestsDeepSeekLLM.stream_complete: {e}")
            raise

    def close(self):
        self.close_shared_session()

    def close_shared_session(self):
        if self._session:
            self._session.close()
            self._session = None
