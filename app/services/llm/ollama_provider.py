from __future__ import annotations

import os
from typing import Any

import requests

from app.config import settings


class OllamaProvider:
    def __init__(self, base_url: str | None = None, model: str | None = None):
        self.base_url = (base_url or settings.ollama_base_url).rstrip("/")
        self.model = model or settings.ollama_model
        self.router_model = settings.ollama_router_model

    def chat(
        self,
        messages: list[dict[str, str]],
        *,
        format_json: bool = False,
        timeout: int = 120,
        model: str | None = None,
    ) -> str:
        selected_model = model or self.model
        payload: dict[str, Any] = {
            "model": selected_model,
            "messages": messages,
            "stream": False,
        }
        if format_json:
            payload["format"] = "json"

        try:
            response = requests.post(f"{self.base_url}/api/chat", json=payload, timeout=timeout)
            response.raise_for_status()
        except requests.ConnectionError as exc:
            raise RuntimeError(
                f"Cannot connect to Ollama at {self.base_url}. Start it with `ollama serve`."
            ) from exc
        except requests.Timeout as exc:
            raise RuntimeError(f"Ollama request timed out while using model `{selected_model}`.") from exc
        except requests.HTTPError as exc:
            detail = response.text if "response" in locals() else str(exc)
            raise RuntimeError(f"Ollama returned an error for model `{selected_model}`: {detail}") from exc
        data = response.json()
        return data.get("message", {}).get("content", "")

    def route(self, messages: list[dict[str, str]], *, format_json: bool = True, timeout: int | None = None) -> str:
        return self.chat(
            messages,
            format_json=format_json,
            timeout=timeout or settings.ollama_router_timeout,
            model=self.router_model,
        )

    def explain(self, messages: list[dict[str, str]], *, timeout: int | None = None) -> str:
        return self.chat(
            messages,
            timeout=timeout or settings.ollama_explain_timeout,
            model=self.model,
        )

    def status(self) -> dict[str, Any]:
        try:
            response = requests.get(f"{self.base_url}/api/tags", timeout=5)
            response.raise_for_status()
            models = response.json().get("models", [])
            model_names = [model.get("name") for model in models]
            return {
                "available": True,
                "base_url": self.base_url,
                "model": self.model,
                "router_model": self.router_model,
                "model_loaded": self.model in model_names,
                "router_model_loaded": self.router_model in model_names,
                "models": model_names,
                "error": None,
            }
        except requests.RequestException as exc:
            return {
                "available": False,
                "base_url": self.base_url,
                "model": self.model,
                "router_model": self.router_model,
                "model_loaded": False,
                "router_model_loaded": False,
                "models": [],
                "error": str(exc),
            }
