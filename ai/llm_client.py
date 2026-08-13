"""Swappable LLM provider interface. Ollama today, Gemini can drop in later.

Downstream code (enrichment, rag, text_to_sql) should only depend on the
LLMClient interface below, never on Ollama specifics directly.
"""
import json
import os
from abc import ABC, abstractmethod

import ollama


class LLMClient(ABC):
    @abstractmethod
    def generate(self, prompt: str, system: str | None = None, json_mode: bool = False) -> str:
        ...

    @abstractmethod
    def embed(self, text: str) -> list[float]:
        ...


class OllamaClient(LLMClient):
    def __init__(self, model: str | None = None, embed_model: str | None = None, host: str | None = None):
        self.model = model or os.environ.get("OLLAMA_MODEL", "qwen2.5:3b")
        self.embed_model = embed_model or os.environ.get("OLLAMA_EMBED_MODEL", "nomic-embed-text")
        self.host = host or os.environ.get("OLLAMA_HOST", "http://localhost:11434")
        self._client = ollama.Client(host=self.host)

    def generate(self, prompt: str, system: str | None = None, json_mode: bool = False) -> str:
        messages = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})
        resp = self._client.chat(
            model=self.model,
            messages=messages,
            format="json" if json_mode else None,
            options={"temperature": 0},
        )
        return resp["message"]["content"]

    def embed(self, text: str) -> list[float]:
        resp = self._client.embeddings(model=self.embed_model, prompt=text)
        return resp["embedding"]


def get_llm_client() -> LLMClient:
    provider = os.environ.get("LLM_PROVIDER", "ollama")
    if provider == "ollama":
        return OllamaClient()
    raise ValueError(f"Unknown LLM_PROVIDER: {provider}")


def parse_json_response(text: str) -> dict:
    """Best-effort JSON extraction, tolerant of stray prose around the object."""
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        start = text.find("{")
        end = text.rfind("}")
        if start != -1 and end != -1 and end > start:
            return json.loads(text[start:end + 1])
        raise
