"""OfferAgent: trazi dobavljace, salje upite za ponude i poredi odgovore."""

from __future__ import annotations

import json
import os
from datetime import datetime
from typing import Any

from src.agents.base_agent import BaseAgent


class OfferAgent(BaseAgent):
    """Agent koji pronalazi dobavljace, salje upite za ponude i poredi odgovore."""

    def __init__(self, name: str = "OfferAgent") -> None:
        super().__init__(name=name)
    def pronadji_direktorijume(self, local_llm, proizvod: str) -> list[str]:
        """Pita LLM koji B2B direktorijumi/platforme najbolje odgovaraju ovoj kategoriji proizvoda."""
        uputstvo = (
            f"Korisnik trazi PRAVE proizvodjace/uzgajivace (ne preprodavce) za: {proizvod}.\n"
            "Navedi 3 najbolja specijalizovana B2B direktorijuma/platforme ili sektorska udruzenja/izvozne "
            "direktorijume na kojima se mogu pronaci pravi proizvodjaci/uzgajivaci ove robe sa kontaktima "
            "(npr. Alibaba, Made-in-China, ThomasNet, Europages, Kompass, ili neki industrijski specificni "
            "direktorijum/udruzenje ako postoji za ovu vrstu robe). "
            "Vrati SAMO gole domene (npr. alibaba.com), jedan po redu, bez https://, bez www, bez "
            "objasnjenja, bez numerisanja."
        )
        odgovor = local_llm.run(uputstvo, language=None)
        domeni = [
            red.strip().lower().replace("https://", "").replace("http://", "").replace("www.", "").rstrip("/")
            for red in odgovor.split("\n") if red.strip()
        ]
        return domeni[:3]
    
    def pronadji_zemlje(self, local_llm, proizvod: str) -> list[str]:
        """Pita LLM koje su zemlje/regioni najpoznatiji po proizvodnji/uzgoju ovog proizvoda."""
        uputstvo = (
            f"Korisnik trazi proizvodjace/uzgajivace za: {proizvod}.\n"
            "Navedi 5 zemalja/regiona koji su NAJPOZNATIJI i NAJVECI proizvodjaci/izvoznici ove "
            "robe u svetu. Vrati SAMO imena zemalja, jedno po redu, bez objasnjenja, bez numerisanja."
        )
        odgovor = local_llm.run(uputstvo, language=None)
        zemlje = [red.strip() for red in odgovor.split("\n") if red.strip()]
        return zemlje[:5]
    def opisi_dobavljaca(self, local_llm, dobavljac: dict, proizvod: str) -> dict:
        """Zamoli LLM da iz sadrzaja sajta izvuce zemlju porekla i kratak opis karakteristika firme."""
        sadrzaj = dobavljac.get("tekst_sajta", "") or dobavljac.get("opis", "")
        uputstvo = (
            f"Evo sadrzaja sa sajta/profila firme '{dobavljac.get('naziv','')}':\n{sadrzaj[:2000]}\n\n"
            f"Korisnik trazi: {proizvod}.\n"
            "Na osnovu ovog sadrzaja, odgovori u DVA kratka reda, tacno u ovom formatu:\n"
            "Zemlja: <zemlja porekla firme, ili 'nepoznato' ako se ne pominje>\n"
            "Opis: <jedna kratka recenica o tome sta firma nudi/koje su karakteristike, ili 'nema dovoljno informacija'>"
        )
        odgovor = local_llm.run(uputstvo, language=None)
        zemlja = "nepoznato"
        opis = "nema dovoljno informacija"
        for red in odgovor.split("\n"):
            if red.lower().startswith("zemlja:"):
                zemlja = red.split(":", 1)[1].strip()
            elif red.lower().startswith("opis:"):
                opis = red.split(":", 1)[1].strip()
        return {"zemlja": zemlja, "opis_karakteristika": opis}

    def pronadji_dobavljace(self, web_agent, local_llm, proizvod: str) -> list[dict]:
            """Pronadji dobavljace pretragom B2B direktorijuma i zemalja poznatih po proizvodnji."""
            domeni = self.pronadji_direktorijume(local_llm, proizvod)
            if not domeni:
                domeni = ["alibaba.com", "made-in-china.com", "europages.com"]

            zemlje = self.pronadji_zemlje(local_llm, proizvod)

            svi_dobavljaci = []
            vidjeni_sajtovi = set()

            for domen in domeni:
                upit = f"site:{domen} {proizvod} manufacturer supplier"
                rezultati = web_agent.pretrazi_dobavljace(upit)
                for d in rezultati:
                    sajt = d.get("sajt", "")
                    if sajt and sajt not in vidjeni_sajtovi:
                        vidjeni_sajtovi.add(sajt)
                        svi_dobavljaci.append(d)

            for zemlja in zemlje:
                upit = f"{proizvod} exporter manufacturer {zemlja}"
                rezultati = web_agent.pretrazi_dobavljace(upit)
                for d in rezultati:
                    sajt = d.get("sajt", "")
                    if sajt and sajt not in vidjeni_sajtovi:
                        vidjeni_sajtovi.add(sajt)
                        d["zemlja_pretrage"] = zemlja
                        svi_dobavljaci.append(d)

            print(f"\nNasla sam {len(svi_dobavljaci)} firmi. Trazim kontakt i karakteristike za svaku...")

            for d in svi_dobavljaci:
                if not d.get("emailovi"):
                    naziv = d.get("naziv", "")
                    if naziv:
                        zvanicni = None
                        sajt_u_tekstu = web_agent.izvuci_sajt_iz_teksta(
                            d.get("tekst_sajta", ""), izbegavaj_domene=domeni
                        )
                        if sajt_u_tekstu:
                            tekst_novog_sajta = web_agent.procitaj_sajt(sajt_u_tekstu)
                            if not tekst_novog_sajta.startswith("Greska"):
                                podaci = web_agent.izvuci_kontakt_i_cene(tekst_novog_sajta)
                                if podaci.get("emailovi"):
                                    zvanicni = {
                                        "sajt": sajt_u_tekstu,
                                        "tekst_sajta": tekst_novog_sajta[:3000],
                                        "emailovi": podaci["emailovi"],
                                        "telefoni": podaci.get("telefoni", []),
                                    }
                        if not zvanicni:
                            zvanicni = web_agent.pronadji_zvanicni_sajt(
                                naziv, local_llm=local_llm, izbegavaj_domene=domeni
                            )
                        if zvanicni:
                            d["zvanicni_sajt"] = zvanicni["sajt"]
                            d["tekst_sajta"] = zvanicni["tekst_sajta"]
                            d["emailovi"] = zvanicni["emailovi"]
                            d["telefoni"] = zvanicni["telefoni"]

                opis = self.opisi_dobavljaca(local_llm, d, proizvod)
                d["zemlja"] = d.get("zemlja_pretrage") or opis["zemlja"]
                d["opis_karakteristika"] = opis["opis_karakteristika"]

            return svi_dobavljaci

    def sastavi_upit(self, local_llm, dobavljac: dict, proizvod: str, kolicina: str = "", dodatni_zahtevi: str = "") -> str:
            """Sastavi profesionalan upit za ponudu, na osnovu stvarnog sadrzaja sajta dobavljaca."""
            sadrzaj_sajta = dobavljac.get("tekst_sajta", "") or dobavljac.get("opis", "")

            uputstvo = (
                f"Evo sadrzaja sa sajta firme '{dobavljac.get('naziv', '')}' ({dobavljac.get('sajt', '')}):\n"
                f"{sadrzaj_sajta[:2000]}\n\n"
                f"Korisnik trazi: {proizvod}.\n\n"
                "Tvoj zadatak: pogledaj sadrzaj sajta iznad i utvrdi sta ova firma KONKRETNO prodaje/nudi. "
                "Napisi kratak, profesionalan email NA SRPSKOM JEZIKU upucen ovoj firmi, u kom trazis ponudu "
                "bas za ono sto oni stvarno nude (a sto je povezano sa onim sto korisnik trazi). "
                "Ne ponavljaj doslovno recenicu korisnikovog upita - formulisi zahtev prirodno, na osnovu "
                "njihove stvarne ponude.\n"
                f"Kolicina: {kolicina if kolicina else 'nije precizirano'}.\n"
                f"Dodatni zahtevi: {dodatni_zahtevi if dodatni_zahtevi else 'nema'}.\n"
                "Pitaj za cenu, uslove placanja i rok isporuke. Budi kratak i konkretan, bez nepotrebnih fraza. "
                "Ne izmisljaj podatke o firmi koje ne postoje u sadrzaju sajta."
            )
            return local_llm.run(uputstvo, language=None)

    def uporedi_ponude(self, local_llm, ponude: list[dict]) -> str:
        """Uporedi prikupljene ponude preko lokalnog LLM-a i predlozi najbolju."""
        if not ponude:
            return "Nema ponuda za poredjenje."

        tekst_ponuda = "\n\n".join(
            f"Ponuda od: {p.get('posiljalac', 'nepoznato')}\n"
            f"Naslov: {p.get('naslov', '')}\n"
            f"Tekst: {p.get('telo', '')}"
            for p in ponude
        )

        uputstvo = (
            "Dobila si vise ponuda od razlicitih dobavljaca. Uporedi ih po ceni, uslovima placanja "
            "i roku isporuke. Za svaku ponudu koja NIJE navela neki podatak, napisi 'nije navedeno' "
            "- ne izmisljaj. Na kraju jasno predlozi koja je najbolja ponuda i zasto.\n\n"
            f"Ponude:\n{tekst_ponuda}"
        )
        return local_llm.run(uputstvo, language=None)

    def sacuvaj_istoriju(self, proizvod: str, ponude: list[dict], preporuka: str, putanja_fajla: str = "memory.json") -> None:
        """Sacuvaj istoriju ponuda u memory.json."""
        try:
            if os.path.exists(putanja_fajla):
                with open(putanja_fajla, "r", encoding="utf-8") as f:
                    memorija = json.load(f)
                if not isinstance(memorija, dict):
                    memorija = {}
            else:
                memorija = {}
        except Exception:
            memorija = {}

        if "ponude_istorija" not in memorija:
            memorija["ponude_istorija"] = []

        memorija["ponude_istorija"].append({
            "datum": datetime.now().strftime("%Y-%m-%d %H:%M"),
            "proizvod": proizvod,
            "broj_ponuda": len(ponude),
            "ponude": ponude,
            "preporuka": preporuka,
        })

        with open(putanja_fajla, "w", encoding="utf-8") as f:
            json.dump(memorija, f, ensure_ascii=False, indent=2)

    def run(self, task: Any) -> str:
        """OfferAgent se koristi preko posebnih metoda, ne direktno preko run()."""
        return "OfferAgent se koristi preko komande 'trazi ponudu' u main.py."