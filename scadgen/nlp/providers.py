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
        image: ImageInput | None = None,
    ) -> str: ...

    @abstractmethod
    def is_available(self) -> bool: ...

    def supports_vision(self) -> bool:
        return False


class OllamaProvider(LLMProvider):
    def __init__(self, base_url: str = "http://localhost:11434", model: str = "mistral"):
        self.base_url = base_url.rstrip("/")
        self.model = model

    def chat(
        self, prompt: str, system: str = "", max_tokens: int = 0,
        image: ImageInput | None = None,
    ) -> str:
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


class AnthropicProvider(LLMProvider):
    def __init__(self, api_key: str, model: str = "claude-sonnet-4-20250514"):
        self.api_key = api_key
        self.model = model
        self._client = None

    def chat(
        self, prompt: str, system: str = "", max_tokens: int = 0,
        image: ImageInput | None = None,
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

        kwargs: dict = {
            "model": self.model,
            "max_tokens": max_tokens or 4096,
            "messages": [{"role": "user", "content": content}],
        }
        if system:
            kwargs["system"] = system

        try:
            resp = client.messages.create(**kwargs)
            return resp.content[0].text
        except Exception as e:
            raise ProviderError(f"Anthropic request failed: {e}") from e

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
        image: ImageInput | None = None,
    ) -> str:
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


def create_provider(config: Config) -> LLMProvider:
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

    # auto-detect: Ollama → Anthropic → OpenAI
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
