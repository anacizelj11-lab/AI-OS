"""Web agent that searches the internet and returns a short summary of results."""

from __future__ import annotations

from typing import Any

from ddgs import DDGS

from src.agents.base_agent import BaseAgent


class WebAgent(BaseAgent):
    """Agent that searches the web using DuckDuckGo and returns top results."""

    def __init__(self, name: str = "WebAgent", max_results: int = 5) -> None:
        super().__init__(name=name)
        self.max_results = max_results

    def run(self, task: Any) -> str:
        """Search the web for the task text and return a formatted summary."""
        query = str(task)

        try:
            results = list(DDGS().text(query, max_results=self.max_results))
        except Exception as exc:
            return f"Greska pri pretrazi interneta: {exc}"

        if not results:
            return "Nisam pronasla nikakve rezultate za tu pretragu."

        lines = []
        for i, r in enumerate(results, start=1):
            title = r.get("title", "Bez naslova")
            url = r.get("href", "")
            snippet = r.get("body", "")
            lines.append(f"{i}. {title}\n{snippet}\n{url}\n")

        return "\n".join(lines)