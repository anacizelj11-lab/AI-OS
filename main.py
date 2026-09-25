from src.core.orchestrator import Orchestrator
from src.agents.local_llm_agent import LocalLLMAgent

orchestrator = Orchestrator()
orchestrator.register_agent("local_llm", LocalLLMAgent())

print("AI-OS je pokrenut. Ukucaj 'kraj' za izlaz.")

while True:
    zadatak = input("Ti: ")
    if zadatak.lower() in ["kraj", "exit", "quit"]:
        print("AI-OS: Cao!")
        break
    odgovor = orchestrator.run_task("local_llm", zadatak)
    print("AI-OS:", odgovor)