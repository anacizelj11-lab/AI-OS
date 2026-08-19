class Orchestrator:
    """A simple registry for AI agents."""

    def __init__(self):
        self.agents = {}

    def register_agent(self, name, agent):
        """Register an agent by name."""
        self.agents[name] = agent