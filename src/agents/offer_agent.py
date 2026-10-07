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

    def pronadji_dobavljace(self, web_agent, local_llm, proizvod: str) -> list[dict]:
            """Pronadji dobavljace preko vise razlicitih upita, za bolju i raznovrsniju pokrivenost."""
            uputstvo = (
                f"Korisnik trazi dobavljace za: {proizvod}.\n"
                "Napravi 3 razlicita kratka upita za pretragu interneta da nadjemo sto raznovrsnije i konkretnije "
                "dobavljace/firme i njihove kontakte - npr. jedan opstiji upit, jedan fokusiran na konkretne "
                "zemlje/regione poznate po toj robi, jedan fokusiran na izvozne/trgovinske kompanije. "
                "Ako se trazeni proizvod odnosi na Srbiju ili lokalno trziste, napisi upite na srpskom. Ako "
                "korisnik izricito trazi dobavljace 'u svetu', globalno, medjunarodno, ili ako se radi o robi "
                "koja se uobicajeno uvozi/ne proizvodi se u Srbiji, napisi upite na ENGLESKOM jeziku jer to "
                "daje bolje globalne rezultate. Vrati SAMO 3 upita, svaki u svom redu, bez numerisanja, bez "
                "navodnika, bez objasnjenja."
            )
            odgovor = local_llm.run(uputstvo, language=None)
            upiti = [red.strip() for red in odgovor.split("\n") if red.strip()]

            svi_dobavljaci = []
            vidjeni_sajtovi = set()

            for upit in upiti[:3]:
                rezultati = web_agent.pretrazi_dobavljace(upit)
                for d in rezultati:
                    sajt = d.get("sajt", "")
                    if sajt and sajt not in vidjeni_sajtovi:
                        vidjeni_sajtovi.add(sajt)
                        svi_dobavljaci.append(d)

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