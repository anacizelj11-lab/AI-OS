"""Base agent definitions for the local AI-OS multi-agent system."""

from __future__ import annotations

from typing import Any


class BaseAgent:
    """Common foundation for all AI agents in the system.

    This class intentionally contains only the shared contract that agent
    implementations need: a name and a task-execution interface. Concrete agent
    behavior, including provider-specific logic or tool access, should live in
    specialized subclasses and separate components.
    """

    def __init__(self, name: str) -> None:
        """Initialize the agent with a human-readable name."""
        if not isinstance(name, str) or not name.strip():
            raise ValueError("Agent name must be a non-empty string.")

        self.name: str = name.strip()

    def run(self, task: Any) -> Any:
        """Execute a task for this agent.

        Subclasses should override this method with their specific behavior.
        The base implementation is intentionally incomplete and raises an error to
        prevent accidental use of an unimplemented agent.
        """
        raise NotImplementedError(
            f"{self.__class__.__name__}.run(task) must be implemented by a subclass."
        )
