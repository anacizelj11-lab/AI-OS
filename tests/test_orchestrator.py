from src.core.orchestrator import Orchestrator


class FakeAgent:
    def run(self, task):
        return f"done: {task}"


def test_orchestrator_routes_task():
    orchestrator = Orchestrator()
    orchestrator.register_agent("test", FakeAgent())

    result = orchestrator.run_task("test", "hello")

    assert result == "done: hello"