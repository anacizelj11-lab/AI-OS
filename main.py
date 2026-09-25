from src.core.orchestrator import Orchestrator
from src.agents.local_llm_agent import LocalLLMAgent
from src.agents.file_agent import FileAgent

orchestrator = Orchestrator()
orchestrator.register_agent("local_llm", LocalLLMAgent())
orchestrator.register_agent("file_agent", FileAgent())

print("AI-OS je pokrenut. Ukucaj 'kraj' za izlaz.")

while True:
    zadatak = input("Ti: ")
    if zadatak.lower() in ["kraj", "exit", "quit"]:
        print("AI-OS: Cao!")
        break
    odgovor = orchestrator.run(zadatak)
    print("AI-OS:", odgovor)