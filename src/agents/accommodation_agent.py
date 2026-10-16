"""Pretraga i obrada ponuda hotela i privatnog smestaja."""

from __future__ import annotations

import re


class AccommodationAgent:
    """Specijalizovani agent za hotelski i privatni smestaj."""

    @staticmethod
    def platforme(proizvod: str, zemlja: str) -> list[str]:
        platforme = [
            "booking.com",
            "airbnb.com",
            "tripadvisor.com",
            "expedia.com",
            "skyscanner.com",
            "kayak.com",
        ]
        return [f"site:{platforma} {proizvod} {zemlja}" for platforma in platforme]

    @staticmethod
    def sastavi_upite(
        proizvod: str,
        zemlja: str,
        siri: bool = False,
    ) -> list[str]:
        upiti = [
            f"{proizvod} hotels {zemlja} official website",
            f"hotels {zemlja} direct booking official website",
            f"private accommodation {zemlja} rental contact",
            f"guesthouse apartment villa {zemlja} owner direct booking",
        ]
        if siri:
            upiti.extend(
                [
                    f"independent hotels {zemlja} official booking",
                    f"private guesthouse villa apartment {zemlja} direct rental",
                ]
            )
        return upiti

    @staticmethod
    def pretrazi(web_agent, upit: str, zemlja: str) -> list[dict]:
        """Pokrece jedan upit za smestaj koristeci zajednicki web agent."""
        return web_agent.pretrazi_dobavljace(upit, zemlja=zemlja)

    @staticmethod
    def izvuci_ocenu_i_recenzije(tekst: str) -> str:
        if not tekst:
            return ""

        delovi = []
        ocena = re.search(
            r"\b(\d(?:[.,]\d{1,2})?)\s*(?:/|out of)\s*10\b",
            tekst,
            re.IGNORECASE,
        )
        if ocena:
            delovi.append(f"Ocena: {ocena.group(1)}/10")
        else:
            zvezdice = re.search(
                r"\b(?:rated|rating|score|ocena)?\s*"
                r"(\d(?:[.,]\d{1,2})?)\s*(?:/ ?5|out of 5|stars?|zvezdica)\b",
                tekst,
                re.IGNORECASE,
            ) or re.search(r"\b(\d)\s*[- ]star\b", tekst, re.IGNORECASE)
            if zvezdice:
                delovi.append(f"Ocena: {zvezdice.group(1)} zvezdica")

        broj_recenzija = re.search(
            r"\b(\d[\d,. ]{0,12})\s+"
            r"(?:verified\s+)?(?:guest\s+)?(?:reviews?|ratings?|recenzija|utisaka)\b",
            tekst,
            re.IGNORECASE,
        )
        if broj_recenzija:
            broj = re.sub(r"\s+", " ", broj_recenzija.group(1)).strip(" ,.")
            delovi.append(f"Recenzije: {broj}")

        utisak = re.search(
            r"(?:guest reviews?|what guests say|customer reviews?|"
            r"reviews?[:\s-]+|gosti kazu|utisci gostiju)[:\s-]*"
            r"[\"“]?(.{20,240}?)(?:[\"”]|(?<=[.!?])\s|$)",
            tekst,
            re.IGNORECASE,
        )
        if utisak:
            citat = re.sub(r"\s+", " ", utisak.group(1)).strip(" \t\r\n\"“”'")
            if citat:
                delovi.append(f"Utisci: {citat}")

        return "; ".join(delovi)
