"""OfferAgent: trazi dobavljace, salje upite za ponude i poredi odgovore."""

from __future__ import annotations

import json
import logging
import os
import re
import unicodedata
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from typing import Any
from urllib.parse import parse_qsl, unquote, urlencode, urlsplit, urlunsplit

from src.agents.accommodation_agent import AccommodationAgent
from src.agents.agency_agent import AgencyAgent
from src.agents.base_agent import BaseAgent
from src.agents.transport_agent import TransportAgent


logger = logging.getLogger(__name__)


class OfferAgent(BaseAgent):
    """Agent koji pronalazi dobavljace, salje upite za ponude i poredi odgovore."""

    def __init__(self, name: str = "OfferAgent") -> None:
        super().__init__(name=name)
        self.accommodation_agent = AccommodationAgent()
        self.agency_agent = AgencyAgent()
        self.transport_agent = TransportAgent()

    def _pretrazi_upite_paralelno(
        self,
        web_agent,
        upiti: list[tuple[str, str]],
    ) -> list[tuple[str, str, list[dict]]]:
        """Pretrazi svaku kategoriju paralelno, uz izolaciju gresaka po upitu."""
        grupisani: dict[str, list[tuple[str, str]]] = {
            "smestaj": [],
            "agencije": [],
            "prevoz": [],
            "ostalo": [],
        }
        for upit, zemlja in upiti:
            kategorija = self._kategorija_usluge(upit)
            if kategorija in {
                "hoteli",
                "privatni_smestaj",
            }:
                grupa = "smestaj"
            elif kategorija.startswith("agencije_"):
                grupa = "agencije"
            elif kategorija in {
                "letovi",
                "trajekti",
                "autobusi",
                "vozovi",
            }:
                grupa = "prevoz"
            else:
                grupa = "ostalo"
            grupisani[grupa].append((upit, zemlja))

        def pretrazi_grupu(stavke: list[tuple[str, str]]) -> list[tuple[str, str, list[dict]]]:
            rezultati_grupe = []
            for upit, zemlja in stavke:
                try:
                    rezultati = self._pretrazi_upit_usluge(web_agent, upit, zemlja)
                except Exception as greska:
                    print(f"Upozorenje: pretraga nije uspela za '{upit}': {greska}")
                    rezultati = []
                rezultati_grupe.append((upit, zemlja, rezultati))
            return rezultati_grupe

        prikupljeni: dict[tuple[str, str], list[dict]] = {}
        with ThreadPoolExecutor(max_workers=len(grupisani)) as executor:
            poslovi = {
                executor.submit(pretrazi_grupu, stavke): grupa
                for grupa, stavke in grupisani.items()
                if stavke
            }
            for posao in as_completed(poslovi):
                grupa = poslovi[posao]
                try:
                    for upit, zemlja, rezultati in posao.result():
                        prikupljeni[(upit, zemlja)] = rezultati
                except Exception as greska:
                    print(f"Upozorenje: pretrage grupe '{grupa}' nisu uspele: {greska}")

        return [
            (upit, zemlja, prikupljeni.get((upit, zemlja), []))
            for upit, zemlja in upiti
        ]
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
            """Zamoli LLM da iz sadrzaja sajta izvuce zemlju porekla, karakteristike i cenu (ako postoji)."""
            sadrzaj = dobavljac.get("tekst_sajta", "") or dobavljac.get("opis", "")
            uputstvo = (
                f"Evo sadrzaja sa sajta/profila firme '{dobavljac.get('naziv','')}':\n{sadrzaj[:2000]}\n\n"
                f"Korisnik trazi: {proizvod}.\n"
                "Na osnovu ovog sadrzaja, odgovori u TRI kratka reda, tacno u ovom formatu:\n"
                "Zemlja: <zemlja porekla firme, ili 'nepoznato' ako se ne pominje>\n"
                "Opis: <jedna kratka recenica o tome sta firma nudi/koje su karakteristike, ili 'nema dovoljno informacija'>\n"
                "Cena: <cena ili cenovni raspon ako se pominje u tekstu, tacno kako pise, ili 'nepoznato' ako se ne pominje>"
            )
            odgovor = local_llm.run(uputstvo, language=None)
            zemlja = "nepoznato"
            opis = "nema dovoljno informacija"
            cena = "nepoznato"
            for red in odgovor.split("\n"):
                if red.lower().startswith("zemlja:"):
                    zemlja = red.split(":", 1)[1].strip()
                elif red.lower().startswith("opis:"):
                    opis = red.split(":", 1)[1].strip()
                elif red.lower().startswith("cena:"):
                    cena = red.split(":", 1)[1].strip()
            return {"zemlja": zemlja, "opis_karakteristika": opis, "cena": cena}
    def odredi_tip_potrage(self, local_llm, proizvod: str) -> str:
            """Pita LLM da li se trazi fizicki proizvod ili usluga/iskustvo (putovanje, smestaj, event...)."""
            uputstvo = (
                f"Korisnik trazi: '{proizvod}'.\n"
                "Da li je ovo FIZICKI PROIZVOD koji se proizvodi/uzgaja/izradjuje (npr. kafa, koza, nabestaj), "
                "ili USLUGA/ISKUSTVO (npr. putovanje, smestaj, konsalting, event, kurs)?\n"
                "Odgovori SAMO jednom recju: 'proizvod' ili 'usluga'."
            )
            odgovor = local_llm.run(uputstvo, language=None).strip().lower()
            if "usluga" in odgovor:
                return "usluga"
            return "proizvod"

    def pronadji_destinacije(self, local_llm, proizvod: str) -> list[str]:
            """Pita LLM koje su zemlje/destinacije najbolje/najpoznatije za ovu vrstu usluge."""
            uputstvo = (
                f"Korisnik trazi uslugu/iskustvo: {proizvod}.\n"
                "Navedi 5 zemalja/destinacija koje su NAJBOLJE ili NAJPOZNATIJE za ovu vrstu usluge. "
                "Vrati SAMO imena zemalja/destinacija, jedno po redu, bez objasnjenja, bez numerisanja."
            )
            odgovor = local_llm.run(uputstvo, language=None)
            destinacije = [red.strip() for red in odgovor.split("\n") if red.strip()]
            return destinacije[:5]

    def rangiraj_dobavljace(self, dobavljaci: list[dict], dodatni_zahtevi: str = "") -> list[dict]:
        """Rangira ponude po ceni, kontaktu, poklapanju zahteva i kompletnosti."""
        cene = [
            broj for d in dobavljaci
            if (broj := self._izvuci_broj_cene(d.get("cena", ""))) is not None
        ]
        najniza = min(cene, default=0)
        najvisa = max(cene, default=0)
        grupe_zahteva = self._grupe_pojmova(dodatni_zahtevi)

        for d in dobavljaci:
            cena_broj = self._izvuci_broj_cene(d.get("cena", ""))
            d["cena_broj"] = cena_broj
            opis = self._normalizuj_tekst(
                " ".join(
                    str(d.get(polje, "") or "")
                    for polje in ("opis_karakteristika", "opis", "tekst_sajta")
                )
            )

            kontakt = bool(d.get("emailovi") or d.get("telefoni") or d.get("platforma_link"))
            skor_kontakta = 30 if d.get("emailovi") else 20 if d.get("telefoni") else 12 if d.get("platforma_link") else 0
            pouzdanost = str(d.get("pouzdanost", "")).lower()
            if pouzdanost == "visok":
                skor_kontakta += 5
            elif pouzdanost == "nizak":
                skor_kontakta -= 5

            skor_poklapanja = 0
            if grupe_zahteva:
                poklapanja = sum(
                    1 for grupa in grupe_zahteva
                    if any(pojam in opis for pojam in grupa)
                )
                skor_poklapanja = 20 * poklapanja / len(grupe_zahteva)

            cena_skor = 0
            if cena_broj is not None:
                if najvisa > najniza:
                    cena_skor = 30 * (najvisa - cena_broj) / (najvisa - najniza)
                else:
                    cena_skor = 30

            ima_opis = bool(
                d.get("opis_karakteristika")
                and d["opis_karakteristika"] != "nema dovoljno informacija"
            )
            ima_zemlju = bool(d.get("zemlja") and d["zemlja"] != "nepoznato")
            kompletnost = sum((cena_broj is not None, kontakt, ima_opis, ima_zemlju))
            d["_skor"] = skor_kontakta + skor_poklapanja + cena_skor + kompletnost * 5
            d["_potpuna_ponuda"] = bool(cena_broj is not None and kontakt and ima_opis and ima_zemlju)

        return sorted(
            dobavljaci,
            key=lambda d: (
                not d["_potpuna_ponuda"],
                -d["_skor"],
                d["cena_broj"] is None,
                d["cena_broj"] if d["cena_broj"] is not None else float("inf"),
            ),
        )

    @staticmethod
    def _normalizuj_tekst(tekst: str) -> str:
        bez_dijakritike = unicodedata.normalize("NFKD", tekst.casefold())
        return "".join(
            znak for znak in bez_dijakritike
            if not unicodedata.combining(znak)
        )

    @classmethod
    def _grupe_pojmova(cls, tekst: str) -> list[set[str]]:
        """Vrati termine kao konceptualne grupe, ukljucujuci cestu srpsko-englesku terminologiju."""
        aliasi = {
            "letov": {"letovanje", "letovanja", "odmor", "vacation", "holiday", "holidays", "travel", "trip", "resort"},
            "odmor": {"odmor", "vacation", "holiday", "holidays", "travel", "trip", "resort"},
            "putov": {"putovanje", "travel", "trip", "tourism"},
            "kaf": {"kafa", "kafu", "coffee"},
            "zelen": {"zelena", "green"},
            "avion": {"avionske", "avionska", "flight", "flights", "airfare", "airline", "ticket", "tickets"},
            "let": {"let", "letovi", "flight", "flights", "airfare", "airline"},
            "karte": {"karte", "ticket", "tickets", "airfare"},
            "smest": {"smestaj", "accommodation", "lodging", "hotel", "apartment", "stay"},
            "hotel": {"hotel", "accommodation", "lodging", "stay"},
            "auto": {"auto", "car", "rental", "hire"},
            "iznajmljiv": {"iznajmljivanje", "rental", "hire"},
            "izlet": {"izleti", "izlet", "excursion", "excursions", "tour", "tours", "activities"},
            "plaz": {"plaza", "beach", "beachfront", "coast", "seaside"},
            "polupansion": {"polupansion", "half", "board", "breakfast", "dinner"},
            "zelena": {"zelena", "green"},
            "green": {"green", "zelena"},
            "coffee": {"coffee", "kafa"},
            "flight": {"flight", "flights", "airfare", "airline", "ticket", "tickets", "avionske", "letovi"},
            "beach": {"beach", "beachfront", "coast", "seaside", "plaza"},
        }
        normalizovan = cls._normalizuj_tekst(tekst)
        reci = re.findall(r"[a-z0-9]+", normalizovan)
        stop_reci = {"i", "u", "za", "sa", "na", "od", "do", "the", "a", "an", "and", "or", "to", "in", "with", "of"}
        grupe = []
        vidjene = set()
        for rec in reci:
            if len(rec) < 2 or rec in stop_reci:
                continue
            grupa = next(
                (set(vrednosti) for prefiks, vrednosti in aliasi.items() if rec.startswith(prefiks)),
                {rec},
            )
            kljuc = frozenset(grupa)
            if kljuc not in vidjene:
                vidjene.add(kljuc)
                grupe.append(grupa)
        return grupe

    @staticmethod
    def _izvuci_broj_cene(cena_tekst: Any) -> float | None:
        if not cena_tekst:
            return None
        brojevi = re.findall(r"\d[\d.,]*", str(cena_tekst))
        if not brojevi:
            return None
        broj = brojevi[0]
        if "," in broj and "." in broj:
            decimalni_separator = "," if broj.rfind(",") > broj.rfind(".") else "."
            hiljadarski_separator = "." if decimalni_separator == "," else ","
            broj = broj.replace(hiljadarski_separator, "").replace(decimalni_separator, ".")
        elif "," in broj or "." in broj:
            separator = "," if "," in broj else "."
            celobrojni, *decimale = broj.split(separator)
            if decimale and len(decimale[-1]) == 3:
                broj = "".join((celobrojni, *decimale))
            else:
                broj = f"{celobrojni}.{''.join(decimale)}"
        try:
            return float(broj)
        except ValueError:
            return None

    def osnovni_domen(self, url: str) -> str:
            """Vraca 'ociscen' domen (bez protokola, www i jezickog prefiksa) da bi se izbegli duplikati."""
            url_za_citanje = url if "://" in url else f"//{url}"
            domen = (urlsplit(url_za_citanje).hostname or "").lower().rstrip(".")
            if domen.startswith("www."):
                domen = domen[4:]

            platforme = {"booking.com", "airbnb.com", "tripadvisor.com"}
            prefiks, separator, ostatak = domen.partition(".")
            if separator and len(prefiks) == 2 and ostatak in platforme:
                domen = ostatak
            return domen

    def sastavi_upite_za_usluge(
        self,
        local_llm,
        proizvod: str,
        dodatni_zahtevi: str,
        zemlja: str,
        kolicina: str = "",
        siri: bool = False,
        polaziste: str = "",
    ) -> list[str]:
        """Generise konkretne pretrage usluge i svakog trazenog dodatnog segmenta."""
        trazi_letove = self._trazi_letove(dodatni_zahtevi)
        trazi_agencije = self._trazi_putovanja(proizvod, dodatni_zahtevi)
        sirenje = (
            "Generisi 3 do 5 novih, sirokih open-web varijacija koje nisu site: upiti. "
            "Trazi lokalne/nezavisne pruzaoce, direktan kontakt, cene i alternative."
            if siri
            else
            "Napravi 2 do 4 kratka, konkretna pretrazivacka upita NA ENGLESKOM."
        )
        uputstvo = (
            f"Usluga/ponuda: '{proizvod}'. Lokacija: '{zemlja}'.\n"
            f"Broj osoba/obim: '{kolicina or 'nije navedeno'}'.\n"
            f"Dodatni zahtevi: '{dodatni_zahtevi or 'nema'}'.\n"
            f"{sirenje} "
            "Obavezno pokrij glavnu uslugu i svaki konkretan dodatni zahtev kao zaseban tip ponude "
            "(npr. ako su navedene avionske karte, napravi poseban upit za flights/air tickets; "
            "ako je naveden auto, poseban za car rental; za izlete, poseban za tours/excursions). "
            "Prevedi zahteve sa srpskog na uobicajene engleske termine, ali ne dodaj usluge koje korisnik nije trazio. "
            "Uključi i open-web upite za zvanicne sajtove pruzalaca i nezavisne pruzaoce usluge, "
            "ne samo platforme; nemoj hardkodovati vrstu usluge. "
            "Svaki upit mora sadrzati lokaciju i relevantan deo korisnikovog konteksta. "
            "Vrati samo upite, jedan po redu, bez numerisanja i objasnjenja."
        )
        odgovor = local_llm.run(uputstvo, language=None)
        upiti = [
            re.sub(r"^\s*(?:[-*]|\d+[.)])\s*", "", red).strip(" \"'")
            for red in odgovor.splitlines()
            if red.strip()
        ]
        upiti.extend(
            [
                f"{proizvod} {zemlja} official website",
                f"independent {proizvod} providers {zemlja} direct contact",
            ]
        )
        if siri:
            upiti.extend(
                [
                    f"{proizvod} {zemlja} local providers contact",
                    f"{proizvod} {zemlja} prices reviews alternatives",
                ]
            )
            if dodatni_zahtevi.strip():
                upiti.append(f"{dodatni_zahtevi} {zemlja} providers contact")
        if trazi_letove or re.search(
            r"\b(?:ferry|ferries|trajekt\w*|brod\w*|bus|buses|autobus\w*|"
            r"coach|intercity|train|trains|rail|voz\w*)\b",
            self._normalizuj_tekst(dodatni_zahtevi),
        ):
            upiti.extend(
                self.transport_agent.sastavi_upite(
                    zemlja,
                    polaziste=polaziste,
                    dodatni_zahtevi=dodatni_zahtevi,
                )
            )
        if trazi_agencije:
            upiti.extend(self.agency_agent.sastavi_upite(proizvod, zemlja, siri=siri))
        if self._trazi_putovanja(proizvod, dodatni_zahtevi):
            upiti.extend(
                self.accommodation_agent.sastavi_upite(
                    proizvod,
                    zemlja,
                    siri=siri,
                )
            )
        jedinstveni_upiti = []
        vidjeni_upiti = set()
        for upit in upiti:
            kljuc = upit.casefold()
            if upit and kljuc not in vidjeni_upiti:
                vidjeni_upiti.add(kljuc)
                jedinstveni_upiti.append(upit)
        return jedinstveni_upiti

    @staticmethod
    def _je_polaziste_u_regionu(polaziste: str) -> bool:
        return TransportAgent.je_polaziste_u_regionu(polaziste)

    @classmethod
    def _trazi_letove(cls, tekst: str) -> bool:
        normalizovan = cls._normalizuj_tekst(tekst)
        return bool(
            re.search(
                r"\b(?:flight|flights|airfare|airline|airlines|avio|avion\w*|let|letovi)\b",
                normalizovan,
            )
            or re.search(r"\bair tickets?\b", normalizovan)
        )

    @classmethod
    def _trazi_putovanja(cls, proizvod: str, dodatni_zahtevi: str = "") -> bool:
        normalizovan = cls._normalizuj_tekst(f"{proizvod} {dodatni_zahtevi}")
        return bool(
            re.search(
                r"\b(?:travel|trip|tourism|tourist|vacation|holiday|holidays|"
                r"letovanje|letovanja|odmor|odmori|putovanje|putovanja|"
                r"turisticka|turisticke|aranzman|aranzmani|tour package|"
                r"travel package|smestaj|accommodation|hotel)\b",
                normalizovan,
            )
        )

    @staticmethod
    def _izvuci_podatke_o_letu(dobavljac: dict, tekst: str) -> dict[str, str]:
        return TransportAgent.izvuci_podatke_o_letu(dobavljac, tekst)

    @staticmethod
    def _normalizuj_url_rezultata(url: str) -> str:
        parsed = urlsplit(url if "://" in url else f"//{url}")
        host = (parsed.hostname or "").lower()
        if host == "www.booking.com" or host.endswith(".booking.com") or host == "booking.com":
            putanja = re.sub(
                r"\.(?:[a-z]{2}(?:-[a-z]{2})?)\.html$",
                ".en-gb.html",
                parsed.path,
                flags=re.IGNORECASE,
            )
            return urlunsplit((parsed.scheme or "https", parsed.netloc, putanja, parsed.query, ""))
        return url

    def _kategorija_usluge(self, upit: str) -> str:
        normalizovan = self._normalizuj_tekst(upit)
        if self._trazi_letove(normalizovan) or any(
            domen in normalizovan
            for domen in ("skyscanner", "google.com/travel/flights", "momondo", "kiwi.com")
        ):
            return "letovi"
        if re.search(r"\b(?:turisticka agencija|agencija putovanja|travel agency|tour operator|"
                     r"package deals|holiday package|aranzman|organizovana putovanja)\b",
                     normalizovan):
            return "agencije_lokalne" if re.search(
                r"\b(?:turisticka agencija|agencija putovanja|aranzman|organizovana putovanja)\b",
                normalizovan,
            ) else "agencije_medjunarodne"
        if re.search(r"\b(?:private accommodation|guesthouse|owner direct|private rental)\b",
                     normalizovan):
            return "privatni_smestaj"
        if "airbnb" in normalizovan:
            return "privatni_smestaj"
        if any(
            token in normalizovan
            for token in (
                "ferryhopper",
                "directferries",
                "ferries.gr",
                "ferry",
                "ferries",
                "trajekt",
                "brod",
            )
        ):
            return "trajekti"
        if any(
            token in normalizovan
            for token in ("getbybus", "flixbus", "busbud", "autobus", "intercity bus")
        ):
            return "autobusi"
        if any(
            token in normalizovan
            for token in ("thetrainline", "trainline", "omio", "train", "rail", "voz")
        ):
            return "vozovi"
        if "booking.com" in normalizovan or "tripadvisor.com" in normalizovan or re.search(
            r"\bhotel", normalizovan
        ):
            return "hoteli"
        return "ostalo"

    @classmethod
    def _tip_sadrzaja_ponude(cls, rezultat: dict) -> str | None:
        naslov = cls._normalizuj_tekst(str(rezultat.get("naziv", "") or ""))
        sadrzaj = cls._normalizuj_tekst(
            " ".join(
                str(rezultat.get(polje, "") or "")
                for polje in ("opis", "tekst_sajta", "sajt")
            )
        )
        signali_hotela = r"\b(?:hotels?|accommodation|lodging|guesthouses?|resorts?|hotel deals)\b"
        signali_letova = (
            r"\b(?:flights?|airfare|airlines?|air tickets?|flight deals|"
            r"avio|letovi|avionske karte)\b"
        )
        naslov_je_hotel = bool(re.search(signali_hotela, naslov))
        naslov_je_let = bool(re.search(signali_letova, naslov))
        if naslov_je_hotel != naslov_je_let:
            return "hoteli" if naslov_je_hotel else "letovi"

        sadrzaj_je_hotel = bool(re.search(signali_hotela, sadrzaj))
        sadrzaj_je_let = bool(re.search(signali_letova, sadrzaj))
        if sadrzaj_je_hotel != sadrzaj_je_let:
            return "hoteli" if sadrzaj_je_hotel else "letovi"
        return None

    def _pretrazi_upit_usluge(self, web_agent, upit: str, zemlja: str) -> list[dict]:
        kategorija = self._kategorija_usluge(upit)
        if kategorija in {"hoteli", "privatni_smestaj"}:
            return self.accommodation_agent.pretrazi(web_agent, upit, zemlja)
        if kategorija.startswith("agencije_"):
            return self.agency_agent.pretrazi(web_agent, upit, zemlja)
        if kategorija == "letovi":
            return self.transport_agent.pretrazi(web_agent, upit, zemlja)
        if kategorija in {"trajekti", "autobusi", "vozovi"}:
            return self.transport_agent.pretrazi(web_agent, upit, zemlja)
        return web_agent.pretrazi_dobavljace(upit, zemlja=zemlja)

    @staticmethod
    def _poruka_o_bot_zastiti(tekst: str) -> bool:
        normalizovan = OfferAgent._normalizuj_tekst(tekst)
        normalizovan = re.sub(r"[^a-z0-9]+", " ", normalizovan)
        fraze = (
            "javascript is disabled",
            "javascript disabled",
            "enable javascript",
            "please enable javascript",
            "verify you are not a robot",
            "verify youre not a robot",
            "verify you re not a robot",
            "verify that you are not a robot",
            "verify that youre not a robot",
            "verify that you re not a robot",
            "youre not a robot",
            "you re not a robot",
        )
        return any(fraza in normalizovan for fraza in fraze)

    def _je_poznata_platforma(self, sajt: str) -> bool:
        domen = self.osnovni_domen(sajt)
        platforme = (
            "booking.com",
            "airbnb.com",
            "tripadvisor.com",
            "expedia.com",
            "skyscanner.com",
            "skyscanner.net",
            "kayak.com",
            "hotels.com",
            "agoda.com",
            "vrbo.com",
            "trivago.com",
            "hostelworld.com",
            "momondo.com",
            "kiwi.com",
        )
        return any(domen == platforma or domen.endswith(f".{platforma}") for platforma in platforme)

    @staticmethod
    def _izvuci_ocenu_i_recenzije(tekst: str) -> str:
        return AccommodationAgent.izvuci_ocenu_i_recenzije(tekst)

    def _rezultat_povezan(
        self,
        rezultat: dict,
        proizvod: str,
        zemlja: str,
        dodatni_zahtevi: str,
        upit: str,
        tip: str,
        kategorija: str = "ostalo",
    ) -> bool:
        naslov = re.split(r"\s*\|\s*", str(rezultat.get("naziv", "")), maxsplit=1)[0]
        opis = " ".join(
            str(rezultat.get(polje, "") or "")
            for polje in ("opis", "tekst_sajta")
        )
        sajt = str(rezultat.get("sajt", "") or "")
        sadrzaj = self._normalizuj_tekst(f"{naslov} {opis} {sajt}")

        if kategorija.startswith("agencije_"):
            if self._je_poznata_platforma(sajt):
                return False
            znaci_agencije = (
                "travel agency", "tour operator", "package deal", "holiday package",
                "travel package", "tour package", "turisticka agencija",
                "agencija putovanja", "organizovana putovanja", "aranzman",
                "holiday operator", "package holiday",
            )
            ima_signal_agencije = any(signal in sadrzaj for signal in znaci_agencije)
            vodic_ili_tura = any(
                signal in sadrzaj
                for signal in ("local guide", "tour guide", "private guide", "walking tour", "day tour")
            )
            ima_aranman = any(
                signal in sadrzaj
                for signal in (
                    "package deal", "holiday package", "travel package", "tour package",
                    "package holiday", "organizovana putovanja", "aranzman",
                )
            )
            lokacije = [
                rec for rec in re.findall(r"[a-z0-9]+", self._normalizuj_tekst(zemlja))
                if len(rec) > 3
            ]
            lokacija_pogodjena = not lokacije or any(lokacija in sadrzaj for lokacija in lokacije)
            return (
                ima_signal_agencije
                and (not vodic_ili_tura or ima_aranman)
                and lokacija_pogodjena
            )

        if kategorija in {"trajekti", "autobusi", "vozovi"}:
            kljucne_reci = {
                "trajekti": ("ferry", "ferries", "trajekt", "brod"),
                "autobusi": ("bus", "buses", "autobus", "coach", "intercity"),
                "vozovi": ("train", "trains", "rail", "voz"),
            }[kategorija]
            lokacije = [
                rec for rec in re.findall(r"[a-z0-9]+", self._normalizuj_tekst(zemlja))
                if len(rec) > 3
            ]
            return (
                any(signal in sadrzaj for signal in kljucne_reci)
                and (not lokacije or any(lokacija in sadrzaj for lokacija in lokacije))
            )

        if kategorija == "letovi":
            lokacije = [
                rec for rec in re.findall(r"[a-z0-9]+", self._normalizuj_tekst(zemlja))
                if len(rec) > 3
            ]
            letovi_mentioned = any(
                pojam in sadrzaj
                for pojam in (
                    "flight", "flights", "airfare", "airline", "aviation",
                    "air ticket", "air tickets", "let", "avio",
                )
            )
            lokacija_pogodjena = not lokacije or any(lokacija in sadrzaj for lokacija in lokacije)
            return letovi_mentioned and lokacija_pogodjena

        if kategorija in {"hoteli", "privatni_smestaj"}:
            lokacije = [
                rec for rec in re.findall(r"[a-z0-9]+", self._normalizuj_tekst(zemlja))
                if len(rec) > 3
            ]
            lokacija_pogodjena = not lokacije or any(lokacija in sadrzaj for lokacija in lokacije)
            signali_smestaja = (
                "hotel", "resort", "accommodation", "lodging", "guesthouse",
                "apartment", "villa", "holiday home", "rental", "stay", "room",
                "smestaj", "apartman",
            )
            smestaj_pogodjen = any(signal in sadrzaj for signal in signali_smestaja)
            return lokacija_pogodjena and smestaj_pogodjen

        if tip == "usluga" and self._poruka_o_bot_zastiti(opis):
            lokacije_url = self._normalizuj_tekst(unquote(sajt))
            grupe_lokacije_url = [
                rec for rec in re.findall(r"[a-z0-9]+", self._normalizuj_tekst(zemlja))
                if len(rec) > 2
            ]
            lokacija_u_url = bool(grupe_lokacije_url) and any(
                rec in lokacije_url for rec in grupe_lokacije_url
            )
            if lokacija_u_url or self._je_poznata_platforma(sajt):
                return True

        grupe_proizvoda = self._grupe_pojmova(proizvod)
        grupe_dodatnih = self._grupe_pojmova(dodatni_zahtevi)
        normalizovan_upit = self._normalizuj_tekst(upit)
        grupe_lokacije = [
            rec for rec in re.findall(r"[a-z0-9]+", self._normalizuj_tekst(zemlja))
            if len(rec) > 2
        ]

        if tip == "usluga" and grupe_lokacije and not any(
            lokacija in sadrzaj for lokacija in grupe_lokacije
        ):
            return False

        poklapanja_proizvoda = sum(
            any(pojam in sadrzaj for pojam in grupa)
            for grupa in grupe_proizvoda
        )
        minimum_poklapanja = max(1, (len(grupe_proizvoda) + 1) // 2)
        proizvod_povezan = bool(grupe_proizvoda) and poklapanja_proizvoda >= minimum_poklapanja

        poklapanja_dodatnih = [
            grupa for grupa in grupe_dodatnih
            if any(pojam in sadrzaj for pojam in grupa)
        ]
        dodatno_povezano = bool(poklapanja_dodatnih)

        if tip == "usluga" and not upit.lower().startswith("site:"):
            eksplicitni_segmenti = [
                grupa for grupa in grupe_dodatnih
                if any(pojam in normalizovan_upit for pojam in grupa)
            ]
            trazi_avionski_prevoz = any(
                rec in self._normalizuj_tekst(dodatni_zahtevi)
                for rec in ("avion", "flight", "airfare", "airline", "letovi")
            )
            upit_za_avionski_prevoz = any(
                rec in normalizovan_upit
                for rec in ("avion", "flight", "airfare", "airline", "letovi")
            ) or bool(re.search(r"\bair tickets?\b", normalizovan_upit))
            if trazi_avionski_prevoz and not upit_za_avionski_prevoz:
                return False
            if trazi_avionski_prevoz and upit_za_avionski_prevoz:
                return any(
                    rec in sadrzaj
                    for rec in ("avion", "flight", "airfare", "airline", "letovi")
                ) or bool(re.search(r"\bair tickets?\b", sadrzaj))
            if eksplicitni_segmenti:
                return any(
                    any(pojam in sadrzaj for pojam in grupa)
                    for grupa in eksplicitni_segmenti
                )

        return proizvod_povezan or dodatno_povezano

    @staticmethod
    def _je_oglasni_url(url: str) -> bool:
        parsed = urlsplit(url if "://" in url else f"//{url}")
        host = (parsed.hostname or "").lower()
        return any(
            host == domen or host.endswith(f".{domen}")
            for domen in ("googleadservices.com", "googlesyndication.com", "doubleclick.net")
        ) or (
            host in {"google.com", "www.google.com"}
            and parsed.path.lower() in {"/aclick", "/url"}
        ) or (
            host in {"bing.com", "www.bing.com"}
            and parsed.path.lower() in {"/aclick", "/ck/a"}
        )

    def _kljuc_rezultata(self, url: str) -> str:
        url = self._normalizuj_url_rezultata(url)
        parsed = urlsplit(url if "://" in url else f"//{url}")
        domen = self.osnovni_domen(url)
        putanja = re.sub(r"/+", "/", parsed.path).rstrip("/").casefold()
        parametri = [
            (key, value) for key, value in parse_qsl(parsed.query, keep_blank_values=True)
            if not key.lower().startswith("utm_")
            and key.lower() not in {
                "gclid", "fbclid", "msclkid", "ref", "source",
                "lang", "lang_code", "selected_language", "label", "aid", "sid",
            }
        ]
        query = urlencode(sorted(parametri))
        return urlunsplit(("", domen, putanja, query, ""))

    @staticmethod
    def _vrednost_popunjena(dobavljac: dict, polja: tuple[str, ...]) -> bool:
        return any(
            dobavljac.get(polje)
            and str(dobavljac[polje]).strip().casefold() not in {"nepoznato", "nema"}
            for polje in polja
        )

    @classmethod
    def _informativnost_ponude(cls, dobavljac: dict) -> int:
        polja_za_ocenu = (
            ("cena", "cene", "cena_karte"),
            ("ocena_i_recenzije",),
            ("opis_karakteristika", "opis"),
            ("emailovi",),
            ("telefoni",),
        )
        return sum(cls._vrednost_popunjena(dobavljac, polja) for polja in polja_za_ocenu)

    @classmethod
    def _ruta_leta(cls, dobavljac: dict) -> str:
        polaziste = str(dobavljac.get("polaziste", "") or "").strip()
        destinacija = str(dobavljac.get("zemlja_pretrage", "") or "").strip()
        sadrzaj = " ".join(
            str(dobavljac.get(polje, "") or "")
            for polje in ("naziv", "opis", "tekst_sajta", "_upit_pretrage")
        )
        normalizovan_sadrzaj = cls._normalizuj_tekst(sadrzaj)
        datum = re.search(
            r"\b(?:\d{4}[-/]\d{1,2}[-/]\d{1,2}|\d{1,2}[-/]\d{1,2}[-/]\d{2,4}|"
            r"(?:jan(?:uary)?|feb(?:ruary)?|mar(?:ch)?|apr(?:il)?|may|jun(?:e)?|"
            r"jul(?:y)?|aug(?:ust)?|sep(?:tember)?|oct(?:ober)?|nov(?:ember)?|"
            r"dec(?:ember)?)\s+\d{1,2}(?:,?\s+\d{4})?|\d{1,2}\s+"
            r"(?:jan(?:uary)?|feb(?:ruary)?|mar(?:ch)?|apr(?:il)?|may|jun(?:e)?|"
            r"jul(?:y)?|aug(?:ust)?|sep(?:tember)?|oct(?:ober)?|nov(?:ember)?|"
            r"dec(?:ember)?)(?:\s+\d{4})?)\b",
            normalizovan_sadrzaj,
        )
        datum_kljuceva = f" | {datum.group(0)}" if datum else ""
        if polaziste and polaziste.casefold() != "nepoznato":
            ruta_fiksna = cls._normalizuj_tekst(f"{polaziste} to {destinacija}")
            return f"{ruta_fiksna}{datum_kljuceva}"

        tekst = normalizovan_sadrzaj
        ruta = re.search(
            r"\bfrom\s+(.+?)\s+to\s+(.+?)(?=\s+(?:flight|flights|ticket|tickets|"
            r"airfare|price|prices|direct|nonstop)\b|$)",
            tekst,
        )
        if ruta:
            return f"{ruta.group(1).strip()} to {ruta.group(2).strip()}{datum_kljuceva}"
        return (cls._normalizuj_tekst(destinacija) or tekst) + datum_kljuceva

    def pronadji_dobavljace(
        self,
        web_agent,
        local_llm,
        proizvod: str,
        zadata_zemlja: str = "",
        dodatni_zahtevi: str = "",
        kolicina: str = "",
        polaziste: str = "",
    ) -> list[dict]:
        """Pronadji dobavljace/pruzaoce usluga, filtriraj i rangiraj rezultate."""
        tip = self.odredi_tip_potrage(local_llm, proizvod)
        print(f"\n(Prepoznato kao: {tip})")

        if zadata_zemlja.strip():
            zemlje = [zadata_zemlja.strip()]
        elif tip == "usluga":
            zemlje = self.pronadji_destinacije(local_llm, proizvod)
        else:
            zemlje = self.pronadji_zemlje(local_llm, proizvod)

        svi_dobavljaci = []
        vidjeni_sajtovi = {}
        rezultati_po_kategoriji: dict[str, list[dict]] = {
            "hoteli": [],
            "privatni_smestaj": [],
            "agencije_lokalne": [],
            "agencije_medjunarodne": [],
            "letovi": [],
            "trajekti": [],
            "autobusi": [],
            "vozovi": [],
            "ostalo": [],
        }
        domeni = []
        rezultati_letova: dict[str, list[dict]] = {}

        def dodaj_rezultate(
            rezultati: list[dict],
            zemlja: str,
            upit: str,
            kategorija: str | None = None,
        ) -> None:
            kategorija = kategorija or self._kategorija_usluge(upit)
            zahtevi_normalizovani = self._normalizuj_tekst(dodatni_zahtevi)
            transportni_segment = {
                "trajekti": r"\b(?:ferry|ferries|trajekt\w*|brod\w*)\b",
                "autobusi": r"\b(?:bus|buses|autobus\w*|coach|intercity)\b",
                "vozovi": r"\b(?:train|trains|rail|voz\w*)\b",
            }.get(kategorija)
            if transportni_segment and not re.search(
                transportni_segment,
                zahtevi_normalizovani,
            ):
                kategorija = "ostalo"
            for dobavljac in rezultati:
                kategorija_rezultata = kategorija
                tip_sadrzaja = self._tip_sadrzaja_ponude(dobavljac)
                if tip_sadrzaja == "hoteli" and kategorija in {"letovi", "ostalo"}:
                    if not self._trazi_putovanja(proizvod, dodatni_zahtevi):
                        continue
                    kategorija_rezultata = "hoteli"
                elif tip_sadrzaja == "letovi" and kategorija in {
                    "hoteli",
                    "privatni_smestaj",
                    "ostalo",
                }:
                    if not self._trazi_letove(dodatni_zahtevi):
                        continue
                    kategorija_rezultata = "letovi"

                sajt = str(dobavljac.get("sajt", "") or "")
                if sajt:
                    sajt = self._normalizuj_url_rezultata(sajt)
                    dobavljac["sajt"] = sajt
                if (
                    not sajt
                    or self._je_oglasni_url(sajt)
                    or not self._rezultat_povezan(
                        dobavljac,
                        proizvod,
                        zemlja,
                        dodatni_zahtevi,
                        upit,
                        tip,
                        kategorija_rezultata,
                    )
                ):
                    continue
                kljuc = self._kljuc_rezultata(sajt)
                if not kljuc:
                    continue
                if kljuc in vidjeni_sajtovi:
                    postojeci = vidjeni_sajtovi[kljuc]
                    if zemlja and not postojeci.get("zemlja_pretrage"):
                        postojeci["zemlja_pretrage"] = zemlja
                    prethodna_kategorija = postojeci.get("kategorija_ponude", "ostalo")
                    if prethodna_kategorija == "ostalo" and kategorija_rezultata != "ostalo":
                        rezultati_po_kategoriji[prethodna_kategorija].remove(postojeci)
                        postojeci["kategorija_ponude"] = kategorija_rezultata
                        rezultati_po_kategoriji.setdefault(kategorija_rezultata, []).append(postojeci)
                    continue
                dobavljac["naziv"] = re.sub(
                    r"\s+", " ",
                    re.split(r"\s*\|\s*", str(dobavljac.get("naziv", "")), maxsplit=1)[0],
                ).strip(" -|")
                dobavljac["zemlja_pretrage"] = zemlja
                dobavljac["_upit_pretrage"] = upit
                dobavljac["kategorija_ponude"] = kategorija_rezultata
                if kategorija_rezultata == "letovi":
                    dobavljac["polaziste"] = polaziste.strip() or "nepoznato"
                    if not polaziste.strip():
                        dobavljac["napomena_rute"] = (
                            "Polaziste nije navedeno; ruta i cena mogu biti samo orijentacione."
                        )
                vidjeni_sajtovi[kljuc] = dobavljac
                svi_dobavljaci.append(dobavljac)
                rezultati_po_kategoriji.setdefault(kategorija_rezultata, []).append(dobavljac)

        if tip == "proizvod":
            domeni = self.pronadji_direktorijume(local_llm, proizvod)
            if not domeni:
                domeni = ["alibaba.com", "made-in-china.com", "europages.com"]

            for domen in domeni:
                upit = f"site:{domen} {proizvod} manufacturer supplier"
                rezultati = web_agent.pretrazi_dobavljace(upit)
                dodaj_rezultate(rezultati, "", upit)

            for zemlja in zemlje:
                upit = f"{proizvod} exporter manufacturer {zemlja}"
                rezultati = web_agent.pretrazi_dobavljace(upit, zemlja=zemlja)
                dodaj_rezultate(rezultati, zemlja, upit)

        elif tip == "usluga":
            domeni = [
                "booking.com",
                "airbnb.com",
                "tripadvisor.com",
                "expedia.com",
                "skyscanner.com",
                "kayak.com",
            ]
            upiti_pretrazeni: set[str] = set()

            pocetni_upiti = []
            for zemlja in zemlje:
                platform_upiti = self.accommodation_agent.platforme(proizvod, zemlja)
                for upit in platform_upiti:
                    try:
                        rezultati = self._pretrazi_upit_usluge(web_agent, upit, zemlja)
                    except Exception as greska:
                        print(f"Upozorenje: pretraga nije uspela za '{upit}': {greska}")
                        rezultati = []
                    upiti_pretrazeni.add(upit.casefold())
                    if self._trazi_letove(upit):
                        rezultati_letova.setdefault(zemlja, []).extend(rezultati)
                    dodaj_rezultate(rezultati, zemlja, upit)

                upiti = []
                upiti.extend(
                    self.sastavi_upite_za_usluge(
                        local_llm,
                        proizvod,
                        dodatni_zahtevi,
                        zemlja,
                        kolicina,
                        polaziste=polaziste,
                    )
                )
                pocetni_upiti.extend(
                    (upit, zemlja)
                    for upit in upiti
                    if upit.casefold() not in upiti_pretrazeni
                )
            for upit, zemlja, rezultati in self._pretrazi_upite_paralelno(
                web_agent,
                pocetni_upiti,
            ):
                upiti_pretrazeni.add(upit.casefold())
                if self._trazi_letove(upit):
                    rezultati_letova.setdefault(zemlja, []).extend(rezultati)
                dodaj_rezultate(rezultati, zemlja, upit)

            je_putovanje = self._trazi_putovanja(proizvod, dodatni_zahtevi)
            ciljne_kategorije = []
            if je_putovanje:
                ciljne_kategorije.extend(["hoteli", "privatni_smestaj"])
                ciljne_kategorije.extend(["agencije_lokalne", "agencije_medjunarodne"])
            if self._trazi_letove(dodatni_zahtevi):
                ciljne_kategorije.append("letovi")
            normalizovani_zahtevi = self._normalizuj_tekst(dodatni_zahtevi)
            if re.search(r"\b(?:ferry|ferries|trajekt\w*|brod\w*)\b", normalizovani_zahtevi):
                ciljne_kategorije.append("trajekti")
            if re.search(
                r"\b(?:bus|buses|autobus\w*|coach|intercity)\b",
                normalizovani_zahtevi,
            ):
                ciljne_kategorije.append("autobusi")
            if re.search(
                r"\b(?:train|trains|rail|voz\w*)\b",
                normalizovani_zahtevi,
            ):
                ciljne_kategorije.append("vozovi")
            treba_siriti = (
                any(
                    len(rezultati_po_kategoriji.get(kategorija, [])) < 2
                    for kategorija in ciljne_kategorije
                )
                if ciljne_kategorije
                else len(svi_dobavljaci) < 8
            )
            if treba_siriti:
                prosireni_upiti = []
                for zemlja in zemlje:
                    upiti = self.sastavi_upite_za_usluge(
                        local_llm,
                        proizvod,
                        dodatni_zahtevi,
                        zemlja,
                        kolicina,
                        siri=True,
                        polaziste=polaziste,
                    )
                    for upit in upiti:
                        if upit.casefold() in upiti_pretrazeni:
                            continue
                        upiti_pretrazeni.add(upit.casefold())
                        prosireni_upiti.append((upit, zemlja))
                for upit, zemlja, rezultati in self._pretrazi_upite_paralelno(
                    web_agent,
                    prosireni_upiti,
                ):
                    if self._trazi_letove(upit):
                        rezultati_letova.setdefault(zemlja, []).extend(rezultati)
                    dodaj_rezultate(rezultati, zemlja, upit)

            for zemlja, rezultati in rezultati_letova.items():
                kontekst_letova = "\n".join(
                    f"- {rezultat.get('naziv', '')}: {rezultat.get('opis', '')} "
                    f"({rezultat.get('sajt', '')})"
                    for rezultat in rezultati[:30]
                )
                odgovor = local_llm.run(
                    "Iz sledecih rezultata pretrage izdvoj samo avio-kompanije koje se "
                    "izricito pominju. Ignorisi sajtove za poredjenje cena i posrednike. "
                    "Vrati najvise 8 redova, tacno u formatu 'Airline: naziv kompanije'. "
                    "Ako nema avio-kompanija, ne vracaj nista.\n"
                    f"Destinacija: {zemlja}\n{ kontekst_letova }",
                    language=None,
                )
                kompanije = []
                for red in odgovor.splitlines():
                    poklapanje = re.match(r"^\s*(?:[-*]|\d+[.)])?\s*Airline:\s*(.+?)\s*$", red, re.I)
                    if poklapanje:
                        ime = poklapanje.group(1).strip(" \"'")
                        if ime and len(ime) <= 80 and ime.casefold() not in {
                            kompanija.casefold() for kompanija in kompanije
                        }:
                            kompanije.append(ime)
                    if len(kompanije) >= 8:
                        break

                for kompanija in kompanije:
                    upit = f'"{kompanija}" official website flights to {zemlja}'
                    rezultati = self.transport_agent.pretrazi(web_agent, upit, zemlja)
                    dodaj_rezultate(rezultati, zemlja, upit)

        print(f"\nNasla sam {len(svi_dobavljaci)} rezultata. Trazim kontakt, cenu i karakteristike za svaku...")

        neuspeli_browser_urlovi: set[str] = set()
        for d in svi_dobavljaci:
            if tip == "proizvod" and not d.get("emailovi"):
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

            tekst_za_ocenu = " ".join(
                str(d.get(polje, "") or "")
                for polje in ("tekst_sajta", "opis")
            )

            if tip == "usluga" and not d.get("emailovi") and not d.get("telefoni"):
                if self._je_poznata_platforma(d.get("sajt", "")):
                    d["platforma_link"] = d.get("sajt", "")

            if tip == "usluga" or not d.get("cene"):
                sajt_za_citanje = d.get("sajt", "")
                if sajt_za_citanje:
                    print(f"   (ucitavam sa browserom: {d.get('naziv','')[:50]})")
                    try:
                        tekst_browser = web_agent.procitaj_sajt_sa_browserom(
                            sajt_za_citanje
                        )
                    except Exception as exc:
                        logger.warning(
                            "Preskacem rezultat %s zbog greske pri ucitavanju: %s",
                            sajt_za_citanje,
                            exc,
                        )
                        neuspeli_browser_urlovi.add(
                            self._kljuc_rezultata(sajt_za_citanje)
                        )
                        continue
                    if tekst_browser.startswith("Greska"):
                        logger.warning(
                            "Preskacem rezultat %s: %s",
                            sajt_za_citanje,
                            tekst_browser,
                        )
                        neuspeli_browser_urlovi.add(
                            self._kljuc_rezultata(sajt_za_citanje)
                        )
                        continue
                    if tekst_browser and not tekst_browser.startswith("Greska"):
                        d["tekst_sajta"] = tekst_browser[:4000]
                        tekst_za_ocenu = f"{tekst_za_ocenu} {tekst_browser}"
                        izvuci_podatke = getattr(web_agent, "izvuci_kontakt_i_cene", None)
                        if callable(izvuci_podatke):
                            podaci = izvuci_podatke(
                                tekst_browser,
                                zemlja=str(d.get("zemlja_pretrage", "")),
                            )
                            d["emailovi"] = list(dict.fromkeys(
                                d.get("emailovi", []) + podaci.get("emailovi", [])
                            ))[:5]
                            d["telefoni"] = list(dict.fromkeys(
                                d.get("telefoni", []) + podaci.get("telefoni", [])
                            ))[:5]
                            d["cene"] = podaci.get("cene", [])

            if d.get("kategorija_ponude") == "letovi":
                d["avio_kompanija"] = "nepoznato"
                d["cena_karte"] = "nepoznato"
                d["tip_leta"] = "nepoznato"
                d.update(
                    self.transport_agent.izvuci_podatke_o_letu(
                        d,
                        " ".join(
                            str(d.get(polje, "") or "")
                            for polje in ("tekst_sajta", "opis")
                        ),
                    )
                )

            ocena_i_recenzije = self.accommodation_agent.izvuci_ocenu_i_recenzije(
                tekst_za_ocenu
            )
            if ocena_i_recenzije:
                d["ocena_i_recenzije"] = ocena_i_recenzije

            opis = self.opisi_dobavljaca(local_llm, d, proizvod)
            d["zemlja"] = (
                opis["zemlja"]
                if opis["zemlja"] != "nepoznato"
                else d.get("zemlja_pretrage") or "nepoznato"
            )
            d["opis_karakteristika"] = opis["opis_karakteristika"]
            d["cena"] = (
                opis["cena"]
                if opis["cena"] != "nepoznato"
                else next(iter(d.get("cene", [])), "nepoznato")
            )

        if neuspeli_browser_urlovi:
            for kategorija, kandidati in rezultati_po_kategoriji.items():
                rezultati_po_kategoriji[kategorija] = [
                    kandidat
                    for kandidat in kandidati
                    if self._kljuc_rezultata(
                        str(kandidat.get("sajt", "") or "")
                    )
                    not in neuspeli_browser_urlovi
                ]

        for kategorija, kandidati in rezultati_po_kategoriji.items():
            po_domenima: dict[str, list[dict]] = {}
            for kandidat in kandidati:
                domen = self.osnovni_domen(str(kandidat.get("sajt", "") or ""))
                po_domenima.setdefault(domen, []).append(kandidat)

            odabrani = []
            for domen, domen_kandidati in po_domenima.items():
                if kategorija == "letovi":
                    po_ruti: dict[str, list[dict]] = {}
                    for kandidat in domen_kandidati:
                        ruta = self._ruta_leta(kandidat)
                        po_ruti.setdefault(ruta, []).append(kandidat)
                    domen_kandidati = [
                        max(ruta_kandidati, key=self._informativnost_ponude)
                        for ruta_kandidati in po_ruti.values()
                    ]
                domen_kandidati.sort(
                    key=self._informativnost_ponude,
                    reverse=True,
                )
                odabrani.extend(domen_kandidati[:2])
            rezultati_po_kategoriji[kategorija] = odabrani

        prikazani_urlovi = {
            self._kljuc_rezultata(str(d.get("sajt", "") or ""))
            for kategorija, kandidati in rezultati_po_kategoriji.items()
            if kategorija != "ostalo"
            for d in kandidati
        }
        prikazani_domeni = {
            self.osnovni_domen(str(d.get("sajt", "") or ""))
            for kategorija, kandidati in rezultati_po_kategoriji.items()
            if kategorija != "ostalo"
            for d in kandidati
        }
        rezultati_po_kategoriji["ostalo"] = [
            d
            for d in rezultati_po_kategoriji.get("ostalo", [])
            if self._kljuc_rezultata(str(d.get("sajt", "") or "")) not in prikazani_urlovi
            and self.osnovni_domen(str(d.get("sajt", "") or "")) not in prikazani_domeni
        ]

        redosled_kategorija = [
            "hoteli",
            "privatni_smestaj",
            "agencije_lokalne",
            "agencije_medjunarodne",
            "letovi",
            "trajekti",
            "autobusi",
            "vozovi",
            "ostalo",
        ]
        sortirani_po_kategoriji = []
        for kategorija in redosled_kategorija:
            kategorijski_rezultati = rezultati_po_kategoriji.get(kategorija, [])
            vidjeni_urlovi_u_kategoriji: set[str] = set()
            for dobavljac in self.rangiraj_dobavljace(
                kategorijski_rezultati,
                dodatni_zahtevi,
            ):
                kljuc = self._kljuc_rezultata(str(dobavljac.get("sajt", "") or ""))
                if kljuc and kljuc not in vidjeni_urlovi_u_kategoriji:
                    vidjeni_urlovi_u_kategoriji.add(kljuc)
                    sortirani_po_kategoriji.append(dobavljac)
        obradjene_kategorije = set(redosled_kategorija)
        for kategorija, kategorijski_rezultati in rezultati_po_kategoriji.items():
            if kategorija not in obradjene_kategorije:
                sortirani_po_kategoriji.extend(
                    self.rangiraj_dobavljace(kategorijski_rezultati, dodatni_zahtevi)
                )
        return sortirani_po_kategoriji

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