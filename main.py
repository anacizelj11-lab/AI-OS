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

            ai_pomoc = input("Da li da AI sastavi tekst email-a? (da/ne): ")

            if ai_pomoc.lower() == "da":
                opis = input("Ukratko opisi o cemu treba email da bude: ")
                jezik_izbor = input("Na kom jeziku? (srpski/engleski/enter za oba): ")

                if jezik_izbor.lower() == "srpski":
                    jezik = "sr"
                elif jezik_izbor.lower() == "engleski":
                    jezik = "en"
                else:
                    jezik = None

                local_llm = orchestrator.agents["local_llm"]
                uputstvo_za_email = (
                    f"Napisi kratak email koji JA saljem drugoj osobi, u prvom licu. "
                    f"Ovo je opis o cemu email treba da govori: {opis} "
                    f"Vazno: ime i prezime koje se pominje napisi tacno onako kako je navedeno, "
                    f"bez ikakve izmene pravopisa ili slova. "
                    f"Ne dodavaj naslov/temu na pocetku teksta, naslov se unosi posebno. "
                    f"Ne koristi markdown formatiranje (zvezdice, tarabe i slicno), pisi obican tekst. "
                    f"Svaki paragraf napisi u kontinuitetu, bez rucnog prelamanja reda usred recenice. "
                    f"Struktuiraj email ovako: prvo pozdrav (npr. 'Postovani,') u svom redu, "
                    f"zatim prazan red, zatim tekst poruke, zatim prazan red, zatim zavrsni pozdrav "
                    f"(npr. 'Srdacan pozdrav,') i u sledecem redu ime i prezime. "
                    f"Pazi na gramaticku ispravnost srpskog jezika, posebno na slaganje roda i broja "
                    f"(na primer: 'obe strane', ne 'oba strana')."
                 )
                tekst = local_llm.run(uputstvo_za_email, language=jezik)
            else:
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