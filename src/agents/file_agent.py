"""File agent that reads text files and returns their content."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from src.agents.base_agent import BaseAgent


class FileAgent(BaseAgent):
    """Agent that reads a text file and returns its contents."""

    def __init__(self, name: str = "FileAgent") -> None:
        super().__init__(name=name)

    def run(self, task: Any) -> str:
        """Extract a file path from the task and return the file's content."""
        text = str(task)
        path = self._extract_path(text)

        if path is None:
            return "Nisam prepoznala putanju do fajla u tvom zahtevu."

        file_path = Path(path)
        if not file_path.exists():
            return f"Fajl ne postoji: {path}"

        try:
            content = file_path.read_text(encoding="utf-8")
        except Exception as exc:
            return f"Greska pri citanju fajla: {exc}"

        return content

    def _extract_path(self, text: str) -> str | None:
        """Very simple path extraction: look for a word containing a dot and slash-like pattern."""
        for word in text.split():
            if "." in word and ("/" in word or "\\" in word or word.count(".") == 1):
                return word.strip('",.')
        return None