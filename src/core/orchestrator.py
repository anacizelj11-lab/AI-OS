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

    def route_task(self, task):
        """Decide which agent should handle a task, based on keywords."""
        text = str(task).lower()

        file_keywords = ["fajl", "dokument", "procitaj", "sacuvaj u fajl"]
        web_keywords = ["pretrazi", "internet", "sajt", "pronadji online"]

        if any(word in text for word in file_keywords):
            return "file_agent"
        if any(word in text for word in web_keywords):
            return "web_agent"

        return "local_llm"

    def run(self, task):
        """Route a task automatically and run it with the chosen agent."""
        name = self.route_task(task)
        return self.run_task(name, task)