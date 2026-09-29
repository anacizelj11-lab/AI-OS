from src.core.orchestrator import Orchestrator
from src.agents.local_llm_agent import LocalLLMAgent
from src.agents.file_agent import FileAgent
from src.agents.web_agent import WebAgent
from src.agents.email_agent import EmailAgent

orchestrator = Orchestrator()
orchestrator.register_agent("local_llm", LocalLLMAgent())
orchestrator.register_agent("file_agent", FileAgent())
orchestrator.register_agent("web_agent", WebAgent())
orchestrator.register_agent("email_agent", EmailAgent())

print("AI-OS je pokrenut. Ukucaj 'kraj' za izlaz.")

while True:
    zadatak = input("Ti: ")
    if zadatak.lower() in ["kraj", "exit", "quit"]:
        print("AI-OS: Cao!")
        break
    odgovor = orchestrator.run(zadatak)
    print("AI-OS:", odgovor)