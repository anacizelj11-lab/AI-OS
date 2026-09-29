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
    if zadatak.lower().startswith("posalji email"):
        primalac = input("Kome saljemo (email adresa)? ")
        naslov = input("Naslov email-a: ")
        print("Unesi tekst email-a (zavrsi praznim redom):")
        linije_teksta = []
        while True:
            linija = input()
            if linija == "":
                break
            linije_teksta.append(linija)
        tekst = "\n".join(linije_teksta)

        print("\n--- PREGLED EMAIL-A ---")
        print(f"Kome: {primalac}")
        print(f"Naslov: {naslov}")
        print(f"Tekst:\n{tekst}")
        print("-----------------------")
        potvrda = input("Da li da posaljem ovaj email? (da/ne): ")

        if potvrda.lower() == "da":
            email_agent = orchestrator.agents["email_agent"]
            rezultat = email_agent.send_email(primalac, naslov, tekst)
            print("AI-OS:", rezultat)
        else:
            print("AI-OS: Email nije poslat.")
        continue
    odgovor = orchestrator.run(zadatak)
    print("AI-OS:", odgovor)