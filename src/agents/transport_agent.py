"""Pretraga avionskog prevoza i izdvajanje detalja leta."""

from __future__ import annotations

import re
import unicodedata
from datetime import datetime


class TransportAgent:
    """Specijalizovani agent za letove, agregatore i avio-kompanije."""

    @staticmethod
    def sastavi_upite(
        zemlja: str,
        polaziste: str = "",
        dodatni_zahtevi: str = "",
    ) -> list[str]:
        zahtevi = TransportAgent._normalizuj_tekst(dodatni_zahtevi)
        trazi_letove = bool(
            re.search(r"\b(?:flight|flights|airfare|airline|airlines|avio|avion|let|letovi)\b", zahtevi)
            or re.search(r"\bair tickets?\b", zahtevi)
        )
        trazi_trajekte = bool(
            re.search(r"\b(?:ferry|ferries|trajekt\w*|brod\w*)\b", zahtevi)
        )
        trazi_autobuse = bool(
            re.search(r"\b(?:bus|buses|autobus\w*|coach|intercity)\b", zahtevi)
        )
        trazi_vozove = bool(
            re.search(r"\b(?:train|trains|rail|voz|vozovi|vozom)\b", zahtevi)
        )

        upiti = []
        if trazi_letove:
            tekuca_godina = datetime.now().year
            ruta_letova = (
                f"flights from {polaziste} to {zemlja}"
                if polaziste.strip()
                else f"flights to {zemlja}"
            )
            upiti.extend(
                [
                    f"site:skyscanner.com {ruta_letova}",
                    f"site:google.com/travel/flights {ruta_letova}",
                    f"site:kayak.com {ruta_letova}",
                    f"site:momondo.com {ruta_letova}",
                    f"site:kiwi.com {ruta_letova}",
                    f"site:esky.pl {ruta_letova}",
                    f"site:esky.ba {ruta_letova}",
                    f"site:esky.rs {ruta_letova}",
                    f"site:edreams.com {ruta_letova}",
                    f"site:wizzair.com {ruta_letova}",
                    f"Skyscanner {ruta_letova} prices",
                    f"Google Flights {ruta_letova} airfare",
                    f"Kayak {ruta_letova} prices",
                    f"Momondo {ruta_letova} airfare",
                    f"Kiwi.com {ruta_letova} prices",
                    (
                        f"{polaziste} to {zemlja} flight tickets"
                        if polaziste.strip()
                        else f"flights to {zemlja} airline"
                    ),
                    (
                        f"direct flights from {polaziste} to {zemlja} {tekuca_godina}"
                        if polaziste.strip()
                        else f"direct flights {zemlja} {tekuca_godina}"
                    ),
                ]
            )
            if polaziste.strip() and TransportAgent.je_polaziste_u_regionu(polaziste):
                upiti.extend(
                    [
                        f"avionska karta {polaziste} {zemlja}",
                        f"letovi iz {polaziste} za {zemlja}",
                    ]
                )
        if trazi_trajekte:
            upiti.extend(
                [
                    f"site:ferryhopper.com ferry {zemlja}",
                    f"site:directferries.com ferry {zemlja}",
                    f"site:ferries.gr ferry {zemlja}",
                    f"ferry operators official website {zemlja}",
                ]
            )
        if trazi_autobuse:
            upiti.extend(
                [
                    f"site:getbybus.com bus {zemlja}",
                    f"site:flixbus.com bus {zemlja}",
                    f"site:busbud.com bus {zemlja}",
                    f"intercity bus operators {zemlja}",
                ]
            )
        if trazi_vozove:
            upiti.extend(
                [
                    f"site:thetrainline.com train {zemlja}",
                    f"site:omio.com train {zemlja}",
                    f"train travel {zemlja} official operator",
                ]
            )
        return upiti

    @staticmethod
    def je_polaziste_u_regionu(polaziste: str) -> bool:
        normalizovano = TransportAgent._normalizuj_tekst(polaziste)
        region = (
            "serbia", "srbija", "belgrade", "beograd", "novi sad", "nis",
            "sarajevo", "bosnia", "herzegovina", "bosna", "croatia", "hrvatska",
            "zagreb", "montenegro", "crna gora", "podgorica", "slovenia",
            "slovenija", "ljubljana", "north macedonia", "macedonia",
            "skopje", "albania", "albanija",
        )
        return any(mesto in normalizovano for mesto in region)

    @staticmethod
    def pretrazi(web_agent, upit: str, zemlja: str) -> list[dict]:
        """Pokrece jedan upit za letove."""
        return web_agent.pretrazi_dobavljace(upit, zemlja=zemlja)

    @staticmethod
    def _normalizuj_tekst(tekst: str) -> str:
        bez_dijakritike = unicodedata.normalize("NFKD", tekst.casefold())
        return "".join(
            znak
            for znak in bez_dijakritike
            if not unicodedata.combining(znak)
        )

    @staticmethod
    def izvuci_podatke_o_letu(dobavljac: dict, tekst: str) -> dict[str, str]:
        podaci: dict[str, str] = {}
        relevantne_linije = [
            re.sub(r"\s+", " ", red).strip()
            for red in re.split(
                r"[\r\n.!?]+",
                " ".join(
                    (
                        str(dobavljac.get("naziv", "") or ""),
                        str(dobavljac.get("opis", "") or ""),
                        str(dobavljac.get("sajt", "") or ""),
                        tekst,
                    )
                ),
            )
            if red.strip()
        ]
        normalizovan_sadrzaj = TransportAgent._normalizuj_tekst(" ".join(relevantne_linije))
        lokacije = {
            rec
            for rec in re.findall(
                r"[a-z0-9]+",
                TransportAgent._normalizuj_tekst(
                    str(dobavljac.get("zemlja_pretrage", "") or "")
                ),
            )
            if len(rec) > 3
        }
        ima_lokaciju = bool(
            lokacije and any(lokacija in normalizovan_sadrzaj for lokacija in lokacije)
        )
        ima_rutu = bool(
            re.search(
                r"\b(?:from|to|via|route|rute|ruta|flights?|letovi|iz|za)\b|->|[-–]\s*[a-z]{3}\b",
                normalizovan_sadrzaj,
            )
        )
        ima_kontekst_rute = ima_lokaciju and ima_rutu
        route_price_lines = []
        route_line_indexes = []
        for indeks, red in enumerate(relevantne_linije):
            normalizovan_red = TransportAgent._normalizuj_tekst(red)
            ima_cenu = bool(re.search(
                r"(?:[$€£]\s?\d[\d,.]*|\b(?:USD|EUR|GBP)\s?\d[\d,.]*|"
                r"\d[\d,.]*\s?\b(?:USD|EUR|GBP)\b)",
                red,
                re.I,
            ))
            linija_ima_lokaciju = bool(
                lokacije and any(lokacija in normalizovan_red for lokacija in lokacije)
            )
            linija_ima_rutu = bool(
                re.search(
                    r"\b(?:from|to|via|ath|jsi|route|rute|ruta)\b|->|[-–]\s*[a-z]{3}\b",
                    normalizovan_red,
                )
            )
            if linija_ima_lokaciju and linija_ima_rutu:
                route_line_indexes.append(indeks)
            if ima_cenu and linija_ima_lokaciju and linija_ima_rutu:
                route_price_lines.append(red)
        route_context_lines = [
            relevantne_linije[indeks]
            for indeks in sorted(
                {
                    bliski_indeks
                    for indeks in route_line_indexes
                    for bliski_indeks in (indeks - 1, indeks, indeks + 1)
                    if 0 <= bliski_indeks < len(relevantne_linije)
                }
            )
        ]

        for red in route_price_lines:
            kompanija = re.search(
                r"\b(?:operated by|airline|carrier|flight with|flights by)\s+"
                r"([A-Z][A-Za-z0-9&'.-]*(?:\s+[A-Z][A-Za-z0-9&'.-]*){0,2})",
                red,
            )
            if not kompanija:
                kompanija = re.search(
                    r"\b([A-Z][A-Za-z0-9&'.-]*(?:\s+[A-Z][A-Za-z0-9&'.-]*){0,2}"
                    r"\s+(?:Airlines?|Airways|Aviation))\b",
                    red,
                )
            if kompanija:
                podaci["avio_kompanija"] = kompanija.group(1).strip()
                break

        if "avio_kompanija" not in podaci and ima_kontekst_rute:
            naslov_i_url = TransportAgent._normalizuj_tekst(
                " ".join(
                    (
                        str(dobavljac.get("naziv", "") or ""),
                        str(dobavljac.get("sajt", "") or ""),
                    )
                )
            )
            poznate_kompanije = (
                (r"\bae gean\b|\baegean(?: airlines?)?\b", "Aegean Airlines"),
                (r"\bryanair\b", "Ryanair"),
                (r"\bair serbia\b|\bairserbia\b", "Air Serbia"),
                (r"\blufthansa\b", "Lufthansa"),
                (r"\bbritish airways\b", "British Airways"),
                (r"\beasy ?jet\b", "easyJet"),
                (r"\bwizz ?air\b", "Wizz Air"),
                (r"\bemirates\b", "Emirates"),
                (r"\bqatar airways\b", "Qatar Airways"),
                (r"\bturkish airlines\b", "Turkish Airlines"),
                (r"\bdelta air lines\b|\bdelta airlines\b", "Delta Air Lines"),
                (r"\bamerican airlines\b", "American Airlines"),
                (r"\bunited airlines\b", "United Airlines"),
                (r"\bair france\b", "Air France"),
                (r"\bklm\b", "KLM"),
                (r"\bswiss international\b|\bswiss\b", "SWISS"),
                (r"\baustrian airlines\b", "Austrian Airlines"),
            )
            for obrazac, ime in poznate_kompanije:
                if re.search(obrazac, naslov_i_url, re.I):
                    podaci["avio_kompanija"] = ime
                    break

        leta_sadrzaj = "\n".join(route_context_lines or route_price_lines)
        if re.search(r"\b(?:direct flight|non[\s-]?stop|nonstop)\b", leta_sadrzaj, re.I):
            podaci["tip_leta"] = "Direktan let"
        elif re.search(
            r"\b(?:\d+\s+stops?|one stop|two stops?|layover|connecting flight|"
            r"with a connection|presedanje)\b",
            leta_sadrzaj,
            re.I,
        ):
            podaci["tip_leta"] = "Let sa presedanjem"

        if route_price_lines or ima_kontekst_rute:
            cena = re.search(
                r"(?:[$€£]\s?\d[\d,.]*|\b(?:USD|EUR|GBP)\s?\d[\d,.]*|"
                r"\d[\d,.]*\s?\b(?:USD|EUR|GBP)\b)",
                "\n".join(route_price_lines or route_context_lines)
                or "\n".join(
                    red
                    for red in relevantne_linije
                    if ima_kontekst_rute and not route_line_indexes
                ),
                re.I,
            )
            if cena:
                podaci["cena_karte"] = cena.group(0).strip().rstrip(".,")

        return podaci
