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