from typing import AsyncGenerator, Optional, List, Dict, Any
import openai
from openai import AsyncOpenAI
from tenacity import retry, stop_after_attempt, wait_exponential

from app.core.config import get_settings


class LLMClient:
    """
    Unified async LLM client for OpenAI-compatible APIs.
    Configured via env vars: LLM_API_KEY, LLM_BASE_URL, LLM_MODEL.
    Works with DeepSeek, OpenAI, and any OpenAI-compatible provider.
    """

    def __init__(self, model: Optional[str] = None):
        settings = get_settings()
        self.api_key = settings.LLM_API_KEY.get_secret_value()
        self.base_url = settings.LLM_BASE_URL
        self.model = model or settings.LLM_MODEL
        self.client = AsyncOpenAI(
            api_key=self.api_key,
            base_url=self.base_url,
            timeout=60.0,
            max_retries=0,  # We handle retries with tenacity
        )
        self.total_tokens_used = 0

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        reraise=True,
    )
    async def chat(
        self,
        messages: List[Dict[str, str]],
        stream: bool = False,
        model: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 4096,
    ) -> Dict[str, Any]:
        """
        Send a chat completion request.
        Returns the full response dict including choices and usage.
        """
        model_name = model or self.model
        try:
            response = await self.client.chat.completions.create(
                model=model_name,
                messages=messages,  # type: ignore[arg-type]
                temperature=temperature,
                max_tokens=max_tokens,
                stream=stream,
            )
            if stream:
                return {"stream": response, "model": model_name}

            usage = response.usage
            if usage and usage.total_tokens:
                self.total_tokens_used += usage.total_tokens

            return {
                "content": response.choices[0].message.content,
                "model": model_name,
                "usage": {
                    "prompt_tokens": usage.prompt_tokens if usage else 0,
                    "completion_tokens": usage.completion_tokens if usage else 0,
                    "total_tokens": usage.total_tokens if usage else 0,
                },
            }
        except openai.APIError as e:
            raise e

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        reraise=True,
    )
    async def chat_stream(
        self,
        messages: List[Dict[str, str]],
        model: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 4096,
    ) -> AsyncGenerator[str, None]:
        """
        Stream chat completion tokens as an async generator.
        Yields content chunks (strings).
        """
        model_name = model or self.model
        try:
            response = await self.client.chat.completions.create(
                model=model_name,
                messages=messages,  # type: ignore[arg-type]
                temperature=temperature,
                max_tokens=max_tokens,
                stream=True,
            )
            async for chunk in response:
                delta = chunk.choices[0].delta.content
                if delta:
                    yield delta
        except openai.APIError as e:
            raise e

    def get_token_usage(self) -> int:
        """Return total tokens used across all chat calls."""
        return self.total_tokens_used
