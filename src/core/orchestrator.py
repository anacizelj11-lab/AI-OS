class Orchestrator:
    """A simple registry for AI agents."""

    def __init__(self):
        self.agents = {}

    def register_agent(self, name, agent):
        """Register an agent by name."""
        self.agents[name] = agent

    def run_task(self, name, task):
        """Run a registered agent by name and return its result."""
        agent = self.agents.get(name)
        if agent is None:
            raise KeyError(f"No agent registered with name: {name}")
        return agent.run(task)