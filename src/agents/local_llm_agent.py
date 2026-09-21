"""Local LLM agent backed by Ollama."""

from __future__ import annotations

import json
from typing import Any
from urllib import error as urllib_error
from urllib import request as urllib_request

from src.agents.base_agent import BaseAgent


class LocalLLMAgent(BaseAgent):
    """Agent that sends a task to a local Ollama model and returns the text response."""

    def __init__(
        self,
        name: str = "LocalLLMAgent",
        model: str = "qwen3.6:27b",
        base_url: str = "http://localhost:11434",
        timeout: float = 60.0,
    ) -> None:
        """Initialize the Ollama-backed agent.

        Args:
            name: Human-readable agent name.
            model: Ollama model name to query.
            base_url: Base URL of the local Ollama service.
            timeout: Network timeout in seconds for the request.
        """
        super().__init__(name=name)

        if not isinstance(model, str) or not model.strip():
            raise ValueError("Model name must be a non-empty string.")
        if not isinstance(base_url, str) or not base_url.strip():
            raise ValueError("Ollama base URL must be a non-empty string.")
        if timeout <= 0:
            raise ValueError("Timeout must be greater than zero.")

        self.model: str = model.strip()
        self.base_url: str = base_url.rstrip("/")
        self.timeout: float = timeout

    def run(self, task: Any) -> str:
        """Send a task to the local Ollama model and return the generated text."""
        prompt = self._normalize_task(task)
        payload = {
            "model": self.model,
            "prompt": prompt,
            "stream": False,
        }
        request = urllib_request.Request(
            f"{self.base_url}/api/generate",
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )

        try:
            with urllib_request.urlopen(request, timeout=self.timeout) as response:
                body = response.read().decode("utf-8")
        except (urllib_error.URLError, TimeoutError, OSError) as exc:
            raise ConnectionError(
                f"Ollama is unavailable at {self.base_url}. "
                "Please ensure the local Ollama service is running and reachable."
            ) from exc

        try:
            data = json.loads(body)
        except json.JSONDecodeError as exc:
            raise ValueError("Ollama returned an invalid JSON response.") from exc

        response_text = data.get("response")
        if not isinstance(response_text, str):
            raise ValueError("Ollama response did not include text content.")

        return response_text.strip()

    def _normalize_task(self, task: Any) -> str:
        """Convert a task value into a string suitable for the Ollama prompt."""
        if task is None:
            return ""
        if isinstance(task, str):
            return task
        if isinstance(task, bytes):
            return task.decode("utf-8", errors="replace")
        return str(task)
