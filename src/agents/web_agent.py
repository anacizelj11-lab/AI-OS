"""Web agent that searches the internet and returns a short summary of results."""

from __future__ import annotations

from typing import Any

from ddgs import DDGS

from src.agents.base_agent import BaseAgent
import os
import re

import requests
from bs4 import BeautifulSoup


class WebAgent(BaseAgent):
    """Agent that searches the web using DuckDuckGo and returns top results."""

    def __init__(self, name: str = "WebAgent", max_results: int = 5) -> None:
        super().__init__(name=name)
        self.max_results = max_results

    def run(self, task: Any) -> str:
        """Search the web for the task text and return a formatted summary."""
        query = str(task)

        try:
            results = list(DDGS().text(query, max_results=self.max_results))
        except Exception as exc:
            return f"Greska pri pretrazi interneta: {exc}"

        if not results:
            return "Nisam pronasla nikakve rezultate za tu pretragu."

        lines = []
        for i, r in enumerate(results, start=1):
            title = r.get("title", "Bez naslova")
            url = r.get("href", "")
            snippet = r.get("body", "")
            lines.append(f"{i}. {title}\n{snippet}\n{url}\n")

        return "\n".join(lines)
    def procitaj_sajt(self, url: str) -> str:
        """Otvara konkretan sajt i vraca citljiv tekst sa stranice (bez HTML oznaka)."""
        try:
            odgovor = requests.get(url, timeout=10, headers={"User-Agent": "Mozilla/5.0"})
            odgovor.raise_for_status()
        except Exception as exc:
            return f"Greska pri otvaranju sajta: {exc}"

        soup = BeautifulSoup(odgovor.text, "html.parser")

        for deo in soup(["script", "style"]):
            deo.decompose()

        tekst = soup.get_text(separator="\n")
        linije = [linija.strip() for linija in tekst.split("\n") if linija.strip()]
        return "\n".join(linije)

    def izvuci_kontakt_i_cene(self, tekst: str) -> dict:
        """Trazi email adrese, telefone i pominjanja cena u datom tekstu."""
        email_obrazac = r"[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+"
        telefon_obrazac = r"(\+?\d[\d \-\(\)]{7,}\d)"
        cena_obrazac = r"(?:\$|€|USD|EUR|RSD|din\.?)\s?\d[\d.,]*|\d[\d.,]*\s?(?:\$|€|USD|EUR|RSD|din\.?)"

        emailovi = list(set(re.findall(email_obrazac, tekst)))
        telefoni = list(set(re.findall(telefon_obrazac, tekst)))
        cene = list(set(re.findall(cena_obrazac, tekst, re.IGNORECASE)))

        return {
            "emailovi": emailovi[:5],
            "telefoni": telefoni[:5],
            "cene": cene[:10],
        }

    def pretrazi_dobavljace(self, upit: str, broj_rezultata: int = 5) -> list[dict]:
            """Pretrazi internet za dobavljace i za svaki pronadjeni sajt izvuci kontakt i opis."""
            try:
                results = list(DDGS().text(upit, max_results=broj_rezultata))
            except Exception as exc:
                return [{"greska": f"Greska pri pretrazi interneta: {exc}"}]

            dobavljaci = []
            for r in results:
                naziv = r.get("title", "Bez naslova")
                url = r.get("href", "")
                opis = r.get("body", "")

                if not url:
                    continue

                tekst_sajta = self.procitaj_sajt(url)
                if tekst_sajta.startswith("Greska"):
                    podaci = {"emailovi": [], "telefoni": [], "cene": []}
                else:
                    podaci = self.izvuci_kontakt_i_cene(tekst_sajta)

                dobavljaci.append({
                    "naziv": naziv,
                    "sajt": url,
                    "opis": opis,
                    "tekst_sajta": tekst_sajta[:3000],
                    "emailovi": podaci.get("emailovi", []),
                    "telefoni": podaci.get("telefoni", []),
                    "pouzdanost": self.oceni_pouzdanost(url),
                })

            return dobavljaci
    def izvuci_sajt_iz_teksta(self, tekst: str, izbegavaj_domene: list[str] | None = None) -> str | None:
        """Pokusaj da pronadje pomen zvanicnog sajta firme unutar vec procitanog teksta (npr. B2B profila)."""
        izbegavaj_domene = izbegavaj_domene or []
        obrazac_domena = r"(?:https?://)?(?:www\.)?([a-zA-Z0-9-]+\.[a-zA-Z]{2,}(?:\.[a-zA-Z]{2,})?)"
        kandidati = re.findall(obrazac_domena, tekst)

        generican = ["gmail.com", "yahoo.com", "hotmail.com", "outlook.com"]

        for domen in kandidati:
            domen_mali = domen.lower()
            if any(izb in domen_mali for izb in izbegavaj_domene):
                continue
            if any(g in domen_mali for g in generican):
                continue
            return f"https://{domen_mali}"

        return None
    def pronadji_zvanicni_sajt(self, naziv: str, local_llm=None, izbegavaj_domene: list[str] | None = None) -> dict | None:
        """Pretrazi ime firme da nadje njen PRAVI zvanicni sajt (van B2B direktorijuma i oglasa) i izvuce kontakt."""
        marketplace_domeni = [
            "alibaba.com", "made-in-china.com", "europages.com", "aliexpress.com",
            "globalsources.com", "tradekey.com", "indiamart.com", "dhgate.com",
            "ec21.com", "exportersindia.com", "thomasnet.com", "kompass.com",
        ]
        ad_domeni = [
            "bing.com/aclick", "google.com/aclick", "googleadservices.com",
            "doubleclick.net", "googlesyndication.com",
        ]
        svi_za_izbegavanje = list(set((izbegavaj_domene or []) + marketplace_domeni + ad_domeni))

        upit = f'"{naziv}" official website contact'

        try:
            results = list(DDGS().text(upit, max_results=5))
        except Exception:
            return None

        kandidati = [
            r for r in results
            if r.get("href") and not any(d in r.get("href", "").lower() for d in svi_za_izbegavanje)
        ]

        if not kandidati:
            return None

        if local_llm:
            lista_za_llm = "\n".join(
                f"{i+1}. {r.get('title','')} - {r.get('href','')} - {r.get('body','')[:150]}"
                for i, r in enumerate(kandidati)
            )
            uputstvo = (
                f"Trazimo zvanicni sajt firme '{naziv}'. Evo rezultata pretrage:\n{lista_za_llm}\n\n"
                "Koji broj rezultata najvise lici na PRAVI zvanicni sajt TE KONKRETNE firme "
                "(ne blog, ne clanak/vodic, ne vladina/nepovezana stranica, ne generican direktorijum)? "
                "Odgovori SAMO brojem. Ako nijedan ne lici na pravi sajt te firme, odgovori 0."
            )
            odgovor = local_llm.run(uputstvo, language=None).strip()
            poklapanje = re.search(r"\d+", odgovor)
            izbor = int(poklapanje.group()) if poklapanje else 0
            if izbor == 0 or izbor > len(kandidati):
                return None
            kandidati = [kandidati[izbor - 1]]

        for r in kandidati:
            url = r.get("href", "")
            tekst_sajta = self.procitaj_sajt(url)
            if tekst_sajta.startswith("Greska"):
                continue

            podaci = self.izvuci_kontakt_i_cene(tekst_sajta)
            emailovi_pravi = [
                e for e in podaci.get("emailovi", [])
                if not any(domen in e.lower() for domen in marketplace_domeni)
            ]
            if not emailovi_pravi:
                continue

            return {
                "sajt": url,
                "tekst_sajta": tekst_sajta[:3000],
                "emailovi": emailovi_pravi,
                "telefoni": podaci.get("telefoni", []),
                "pouzdanost": self.oceni_pouzdanost(url),
            }

        return None
    def preuzmi_fajlove(self, url: str, folder: str = "preuzeto") -> list:
        """Pronalazi linkove ka PDF/cenovnik fajlovima na stranici i preuzima ih na disk."""
        try:
            odgovor = requests.get(url, timeout=10, headers={"User-Agent": "Mozilla/5.0"})
            odgovor.raise_for_status()
        except Exception as exc:
            return [f"Greska: {exc}"]

        soup = BeautifulSoup(odgovor.text, "html.parser")
        linkovi = soup.find_all("a", href=True)

        os.makedirs(folder, exist_ok=True)
        preuzeti = []

        for link in linkovi:
            href = link["href"]
            if href.lower().endswith((".pdf", ".xlsx", ".csv")):
                puna_putanja = href if href.startswith("http") else requests.compat.urljoin(url, href)
                ime_fajla = os.path.join(folder, os.path.basename(puna_putanja.split("?")[0]))
                try:
                    sadrzaj = requests.get(puna_putanja, timeout=15)
                    with open(ime_fajla, "wb") as f:
                        f.write(sadrzaj.content)
                    preuzeti.append(ime_fajla)
                except Exception:
                    continue

        return preuzeti

    def oceni_pouzdanost(self, url: str) -> str:
        """Jednostavno pravilo: zvanicni sajt kompanije dobija vise poena od bloga/foruma."""
        domen = url.lower()
        if any(rec in domen for rec in ["blog", "forum", "reddit", "quora", "medium.com"]):
            return "nizak"
        if "wikipedia" in domen:
            return "srednji"
        return "visok"