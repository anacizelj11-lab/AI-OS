from src.agents.local_llm_agent import LocalLLMAgent

agent = LocalLLMAgent()
odgovor = agent.run("Koji je glavni grad Srbije? Odgovori prvo na srpskom, zatim na engleskom.")
print(odgovor)