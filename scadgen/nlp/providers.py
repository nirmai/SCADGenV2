from __future__ import annotations

import json
from abc import ABC, abstractmethod

import requests

from scadgen.config import Config
from scadgen.exceptions import ProviderError, ProviderUnavailableError


class LLMProvider(ABC):
    @abstractmethod
    def chat(self, prompt: str, system: str = "") -> str: ...

    @abstractmethod
    def is_available(self) -> bool: ...


class OllamaProvider(LLMProvider):
    def __init__(self, base_url: str = "http://localhost:11434", model: str = "mistral"):
        self.base_url = base_url.rstrip("/")
        self.model = model

    def chat(self, prompt: str, system: str = "") -> str:
        messages = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})

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


class OpenAIProvider(LLMProvider):
    def __init__(self, api_key: str, model: str = "gpt-4o-mini"):
        self.api_key = api_key
        self.model = model
        self._client = None

    def chat(self, prompt: str, system: str = "") -> str:
        client = self._get_client()
        messages = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})

        try:
            resp = client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=0.2,
                max_tokens=1000,
                response_format={"type": "json_object"},
            )
            return resp.choices[0].message.content or ""
        except Exception as e:
            raise ProviderError(f"OpenAI request failed: {e}") from e

    def is_available(self) -> bool:
        return bool(self.api_key)

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
    if config.provider == "openai":
        if not config.openai_api_key:
            raise ProviderUnavailableError("OPENAI_API_KEY not set")
        return OpenAIProvider(config.openai_api_key, config.openai_model)

    # auto-detect: try Ollama first, then OpenAI
    ollama = OllamaProvider(config.ollama_url, config.ollama_model)
    if ollama.is_available():
        return ollama
    if config.openai_api_key:
        return OpenAIProvider(config.openai_api_key, config.openai_model)

    raise ProviderUnavailableError(
        "No LLM provider available. Start Ollama or set OPENAI_API_KEY."
    )
