from __future__ import annotations

import base64
import json
from abc import ABC, abstractmethod
from dataclasses import dataclass
from pathlib import Path

import requests

from scadgen.config import Config
from scadgen.exceptions import ProviderError, ProviderUnavailableError

_MEDIA_TYPES = {
    ".png": "image/png",
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".gif": "image/gif",
    ".webp": "image/webp",
}


@dataclass
class ImageInput:
    """A reference image to pass alongside a prompt for vision models."""

    data_b64: str
    media_type: str

    @classmethod
    def from_path(cls, path: str) -> ImageInput:
        p = Path(path)
        media_type = _MEDIA_TYPES.get(p.suffix.lower())
        if media_type is None:
            raise ProviderError(
                f"Unsupported image type '{p.suffix}'. Use PNG, JPEG, GIF, or WebP."
            )
        data = base64.standard_b64encode(p.read_bytes()).decode("ascii")
        return cls(data_b64=data, media_type=media_type)


class LLMProvider(ABC):
    @abstractmethod
    def chat(
        self, prompt: str, system: str = "", max_tokens: int = 0,
        image: ImageInput | None = None, thinking: bool = True,
    ) -> str:
        """Send a prompt and return the model's text response.

        `thinking` asks for extended reasoning where the provider supports
        it. Turn it off for structured output (JSON) where reasoning tokens
        only compete with the answer for the token budget; leave it on for
        open-ended generation. Providers without extended thinking ignore it.
        """
        ...

    @abstractmethod
    def is_available(self) -> bool: ...

    def supports_vision(self) -> bool:
        return False


_OLLAMA_VISION_HINTS = (
    "llava", "bakllava", "vision", "moondream", "minicpm-v",
    "-vl", "qwen2-vl", "qwen2.5vl", "gemma3", "llama3.2-vision",
)


class OllamaProvider(LLMProvider):
    def __init__(self, base_url: str = "http://localhost:11434", model: str = "mistral"):
        self.base_url = base_url.rstrip("/")
        self.model = model

    def supports_vision(self) -> bool:
        name = self.model.lower()
        return any(hint in name for hint in _OLLAMA_VISION_HINTS)

    def chat(
        self, prompt: str, system: str = "", max_tokens: int = 0,
        image: ImageInput | None = None, thinking: bool = True,
    ) -> str:
        """`thinking` is ignored — Ollama has no extended-thinking control."""
        messages = []
        if system:
            messages.append({"role": "system", "content": system})
        user_msg: dict = {"role": "user", "content": prompt}
        if image is not None:
            # Ollama multimodal models accept base64 images on the message.
            user_msg["images"] = [image.data_b64]
        messages.append(user_msg)

        try:
            resp = requests.post(
                f"{self.base_url}/api/chat",
                json={"model": self.model, "messages": messages, "stream": False},
                timeout=120,
            )
            resp.raise_for_status()
            return resp.json()["message"]["content"]
        except requests.RequestException as e:
            raise ProviderError(f"Ollama request failed: {e}") from e

    def is_available(self) -> bool:
        try:
            resp = requests.get(f"{self.base_url}/api/tags", timeout=2)
            return resp.status_code == 200
        except requests.RequestException:
            return False


def _describe_response(resp) -> str:
    """Summarize why a response carried no text block.

    stop_reason='max_tokens' means the output was truncated; thinking_tokens
    shows how much of the budget reasoning consumed.
    """
    parts = [f"stop_reason={getattr(resp, 'stop_reason', '?')}"]

    usage = getattr(resp, "usage", None)
    if usage is not None:
        parts.append(f"output_tokens={getattr(usage, 'output_tokens', '?')}")
        details = getattr(usage, "output_tokens_details", None)
        if details is not None:
            parts.append(
                f"thinking_tokens={getattr(details, 'thinking_tokens', '?')}"
            )

    block_types = [getattr(b, "type", "?") for b in getattr(resp, "content", [])]
    parts.append(f"blocks={block_types}")
    return ", ".join(parts)


def _thinking_budget(max_tokens: int) -> int:
    """Tokens to allow extended thinking, reserving the rest for the answer.

    The API requires budget_tokens >= 1024 and strictly < max_tokens. When
    the budget is too small to satisfy both, return 0 so no thinking config
    is sent and the API default applies.
    """
    half = max_tokens // 2
    if half < 1024 or max_tokens <= 1024:
        return 0
    return min(half, max_tokens - 1024)


class AnthropicProvider(LLMProvider):
    def __init__(self, api_key: str, model: str = "claude-sonnet-5"):
        self.api_key = api_key
        self.model = model
        self._client = None

    def chat(
        self, prompt: str, system: str = "", max_tokens: int = 0,
        image: ImageInput | None = None, thinking: bool = True,
    ) -> str:
        client = self._get_client()

        if image is not None:
            content: list = [
                {
                    "type": "image",
                    "source": {
                        "type": "base64",
                        "media_type": image.media_type,
                        "data": image.data_b64,
                    },
                },
                {"type": "text", "text": prompt},
            ]
        else:
            content = prompt

        budget = max_tokens or 4096
        kwargs: dict = {
            "model": self.model,
            "max_tokens": budget,
            "messages": [{"role": "user", "content": content}],
        }
        if system:
            kwargs["system"] = system

        # Thinking configs to try, in order. Each rung handles a distinct
        # failure: reasoning crowding out the answer, then a model/API that
        # doesn't recognize the parameter at all. Note that omitting the
        # parameter does NOT disable thinking — the API's default is ON —
        # so "disabled" has to be sent explicitly.
        attempts: list[dict | None] = []
        thinking_budget = _thinking_budget(budget) if thinking else 0
        if thinking_budget:
            # Cap how much of the budget reasoning may consume so the
            # remainder is reserved for the actual answer.
            attempts.append(
                {"type": "enabled", "budget_tokens": thinking_budget}
            )
        attempts.append({"type": "disabled"})
        attempts.append(None)

        diagnostics = ""
        last_error: ProviderError | None = None
        for config in attempts:
            if config is None:
                kwargs.pop("thinking", None)
            else:
                kwargs["thinking"] = config
            try:
                text, diagnostics = self._request_text(client, kwargs)
            except ProviderError as e:
                last_error = e
                continue
            if text is not None:
                return text

        if last_error is not None:
            raise last_error
        raise ProviderError(
            f"Anthropic returned no text block (model: {self.model}, "
            f"{diagnostics})"
        )

    def _request_text(self, client, kwargs: dict) -> tuple[str | None, str]:
        """Make one request.

        Returns (text, diagnostics) where text is the response's text block
        or None if it has none, and diagnostics summarizes why — stop reason
        and token usage make a missing text block self-explanatory.
        """
        try:
            resp = client.messages.create(**kwargs)
        except Exception as e:
            raise ProviderError(f"Anthropic request failed: {e}") from e

        # Extended-thinking models may prepend a ThinkingBlock (or other
        # non-text block) before the actual text block — find the text one.
        for block in resp.content:
            if getattr(block, "type", None) == "text":
                return block.text, ""

        return None, _describe_response(resp)

    def is_available(self) -> bool:
        return bool(self.api_key)

    def supports_vision(self) -> bool:
        return True

    def _get_client(self):
        if self._client is None:
            try:
                import anthropic

                self._client = anthropic.Anthropic(api_key=self.api_key)
            except ImportError:
                raise ProviderUnavailableError(
                    "anthropic package not installed. Install with: pip install anthropic"
                )
        return self._client


class OpenAIProvider(LLMProvider):
    def __init__(self, api_key: str, model: str = "gpt-4o-mini"):
        self.api_key = api_key
        self.model = model
        self._client = None

    def chat(
        self, prompt: str, system: str = "", max_tokens: int = 0,
        image: ImageInput | None = None, thinking: bool = True,
    ) -> str:
        """`thinking` is ignored — no extended-thinking control on this API."""
        client = self._get_client()
        messages = []
        if system:
            messages.append({"role": "system", "content": system})

        if image is not None:
            data_uri = f"data:{image.media_type};base64,{image.data_b64}"
            messages.append({
                "role": "user",
                "content": [
                    {"type": "text", "text": prompt},
                    {"type": "image_url", "image_url": {"url": data_uri}},
                ],
            })
        else:
            messages.append({"role": "user", "content": prompt})

        try:
            resp = client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=0.2,
                max_tokens=max_tokens or 4096,
            )
            return resp.choices[0].message.content or ""
        except Exception as e:
            raise ProviderError(f"OpenAI request failed: {e}") from e

    def is_available(self) -> bool:
        return bool(self.api_key)

    def supports_vision(self) -> bool:
        return True

    def _get_client(self):
        if self._client is None:
            try:
                import openai

                self._client = openai.OpenAI(api_key=self.api_key)
            except ImportError:
                raise ProviderUnavailableError(
                    "openai package not installed. Install with: pip install scadgen[openai]"
                )
        return self._client


def create_provider(config: Config, prefer_vision: bool = False) -> LLMProvider:
    if config.provider == "ollama":
        return OllamaProvider(config.ollama_url, config.ollama_model)
    if config.provider == "anthropic":
        if not config.anthropic_api_key:
            raise ProviderUnavailableError("ANTHROPIC_API_KEY not set")
        return AnthropicProvider(config.anthropic_api_key, config.anthropic_model)
    if config.provider == "openai":
        if not config.openai_api_key:
            raise ProviderUnavailableError("OPENAI_API_KEY not set")
        return OpenAIProvider(config.openai_api_key, config.openai_model)

    # auto-detect. When a reference image is in play, prefer a cloud
    # vision-capable provider over local Ollama (whose vision support
    # depends on the loaded model and can't be assumed).
    if prefer_vision:
        if config.anthropic_api_key:
            return AnthropicProvider(config.anthropic_api_key, config.anthropic_model)
        if config.openai_api_key:
            return OpenAIProvider(config.openai_api_key, config.openai_model)

    ollama = OllamaProvider(config.ollama_url, config.ollama_model)
    if ollama.is_available():
        return ollama
    if config.anthropic_api_key:
        return AnthropicProvider(config.anthropic_api_key, config.anthropic_model)
    if config.openai_api_key:
        return OpenAIProvider(config.openai_api_key, config.openai_model)

    raise ProviderUnavailableError(
        "No LLM provider available. Start Ollama, or set ANTHROPIC_API_KEY / OPENAI_API_KEY."
    )
