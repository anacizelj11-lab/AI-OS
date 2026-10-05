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

            while True:
                print("\n--- PREGLED EMAIL-A ---")
                print(f"Kome: {primalac}")
                print(f"Naslov: {naslov}")
                print(f"Tekst:\n{tekst}")
                print("-----------------------")
                potvrda = input("Da li da posaljem ovaj email? (da/ne/izmeni): ")

                if potvrda.lower() == "da":
                    email_agent = orchestrator.agents["email_agent"]
                    rezultat = email_agent.send_email(primalac, naslov, tekst)
                    print("AI-OS:", rezultat)
                    break
                elif potvrda.lower() == "izmeni":
                    izmena = input("Sta da izmenim? (ukratko opisi): ")
                    uputstvo_za_izmenu = (
                        f"Ovo je prethodni nacrt email-a:\n{tekst}\n\n"
                        f"Primeni sledece izmene na ovaj email: {izmena}\n"
                        f"Vrati ceo ispravljen tekst email-a. "
                        f"Ne koristi markdown formatiranje. Ne dodavaj naslov na pocetku. "
                        f"Pisi u kontinuitetu bez rucnog prelamanja redova usred recenice. "
                        f"Zadrzi strukturu: pozdrav, tekst, zavrsni pozdrav, ime i prezime."
                    )
                    tekst = local_llm.run(uputstvo_za_izmenu, language=jezik)
                else:
                    print("AI-OS: Email nije poslat.")
                    break
            continue
           
    if zadatak.lower().startswith("istrazi"):
        tema = input("Sta da istrazim u dubinu (npr. proizvod, cena, dobavljaci)? ")

        web_agent = orchestrator.agents["web_agent"]
        local_llm = orchestrator.agents["local_llm"]

        uputstvo_za_upite = (
            f"Korisnik zeli dubinsko istrazivanje na internetu o sledecoj temi:\n"
            f"'{tema}'\n\n"
            f"Napravi 4 kratka, precizna upita za pretragu interneta (stil kao za Google pretragu) "
            f"koji bi pokrili RAZLICITE aspekte ove teme (npr. opsta trziste/cene, konkretni brojevi "
            f"i statistika, imena i kontakti kompanija/proizvodjaca/uzgajivaca ako se pominju u temi). "
            f"Kada trazis kompanije, proizvodjace ili uzgajivace, koristi fraze tipa 'top exporting "
            f"companies list', 'leading producers ranking', 'list of' - takve fraze obicno pronalaze "
            f"prave liste i imena kompanija, za razliku od opstih pojmova. "
            f"Ako se tema odnosi na Srbiju, napisi upite na srpskom jeziku. Ako se tema odnosi na "
            f"svet/globalno ili ne pominje konkretnu zemlju, napisi upite na engleskom jeziku jer ce "
            f"to dati bolje globalne rezultate. "
            f"Svaki upit napisi u svom redu, bez numerisanja, bez dodatnih objasnjenja - samo sami "
            f"upiti za pretragu."
        )
        predlog_upita = local_llm.run(uputstvo_za_upite, language=None)
        upiti = [linija.strip() for linija in predlog_upita.split("\n") if linija.strip()]

        svi_rezultati = []
        for upit in upiti:
            rezultat_pretrage = web_agent.run(upit)
            svi_rezultati.append(f"### Rezultati za upit: '{upit}'\n{rezultat_pretrage}")

        sirovi_rezultati = "\n\n".join(svi_rezultati)

        jezik_izbor = input("Na kom jeziku da napravim izvestaj? (srpski/engleski/enter za oba): ")
        if jezik_izbor.lower() == "srpski":
            jezik = "sr"
        elif jezik_izbor.lower() == "engleski":
            jezik = "en"
        else:
            jezik = None

        uputstvo_za_izvestaj = (
            f"Na osnovu sledecih sirovih rezultata pretrage interneta, napravi detaljan i dubok "
            f"izvestaj o temi: '{tema}'.\n\n"
            f"Sirovi rezultati pretrage:\n{sirovi_rezultati}\n\n"
            f"Izvestaj treba da sadrzi: kratak opis teme, kljucne cinjenice i brojeve (cene, kolicine, "
            f"nazive kompanija/proizvodjaca/uzgajivaca i njihove kontakte ako se pominju), i na kraju "
            f"listu izvora (linkova) koje si koristila. Obradi SVE delove teme koje je korisnik naveo - "
            f"ne preskaci nijedan deo pitanja. Ne izmisljaj podatke koji nisu u rezultatima pretrage - "
            f"ako nesto nije pronadjeno, jasno to navedi. Ne koristi markdown formatiranje (zvezdice, "
            f"tarabe), pisi obican tekst."
        )
        izvestaj = local_llm.run(uputstvo_za_izvestaj, language=jezik)

        print("\n--- IZVESTAJ ---")
        print(izvestaj)
        print("----------------")
        continue
    odgovor = orchestrator.run(zadatak)
    print("AI-OS:", odgovor)