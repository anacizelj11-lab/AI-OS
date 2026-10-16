"""Prikuplja putne informacije prilagodjene destinaciji i putniku."""

from __future__ import annotations

import re


class DestinationInfoAgent:
    """Istrazuje vreme, ulazne uslove, valutu, aktivnosti i lokalni prevoz."""

    @staticmethod
    def _odgovor_sa_izvorima(odgovor: str, izvori: list[dict[str, str]]) -> str:
        odgovor = re.split(
            r"(?im)^\s*(?:izvori|sources|references)\s*:?\s*$",
            odgovor,
            maxsplit=1,
        )[0].rstrip()
        brojevi_izvora = {str(indeks) for indeks in range(1, len(izvori) + 1)}
        korisceni_brojevi: set[str] = set()

        def proveri_referencu(poklapanje: re.Match[str]) -> str:
            broj = poklapanje.group(1)
            if broj not in brojevi_izvora:
                return ""
            korisceni_brojevi.add(broj)
            return poklapanje.group(0)

        odgovor = re.sub(r"\[(\d+)\]", proveri_referencu, odgovor)
        if not korisceni_brojevi:
            return odgovor

        spisak = "\n".join(
            f"[{broj}] {izvori[int(broj) - 1]['naziv']} — {izvori[int(broj) - 1]['sajt']}"
            for broj in sorted(korisceni_brojevi, key=int)
        )
        return f"{odgovor}\n\nIzvori:\n{spisak}"

    @staticmethod
    def _upiti(destinacija: str, period: str, drzavljanstvo: str) -> list[str]:
        drzavljanstvo_kontekst = f" {drzavljanstvo} passport" if drzavljanstvo else ""
        return [
            f"{destinacija} weather forecast {period}",
            f"{drzavljanstvo_kontekst.strip()} visa entry requirements {destinacija}",
            f"{destinacija} currency exchange rate",
            f"{destinacija} attractions activities events {period}",
            f"{drzavljanstvo_kontekst.strip()} travel advisory safety {destinacija}",
            f"{destinacija} local public transport taxi car rental",
        ]

    def istrazi(
        self,
        web_agent,
        local_llm,
        destinacija: str,
        period: str = "",
        drzavljanstvo: str = "",
    ) -> str:
        """Prikupi pretrazive izvore i sintetizuje samo potkrepljene informacije."""
        rezultati = []
        izvori: list[dict[str, str]] = []
        brojevi_po_urlu: dict[str, int] = {}
        for upit in self._upiti(destinacija, period, drzavljanstvo):
            try:
                for rezultat in web_agent.pretrazi_dobavljace(upit, zemlja=destinacija):
                    sajt = str(rezultat.get("sajt", "") or "").strip()
                    broj_izvora = brojevi_po_urlu.get(sajt) if sajt else None
                    if sajt and broj_izvora is None:
                        izvori.append(
                            {
                                "naziv": str(rezultat.get("naziv", "") or "Nepoznat izvor"),
                                "sajt": sajt,
                            }
                        )
                        broj_izvora = len(izvori)
                        brojevi_po_urlu[sajt] = broj_izvora
                    rezultati.append(
                        {
                            "upit": upit,
                            "naziv": rezultat.get("naziv", ""),
                            "opis": rezultat.get("opis", ""),
                            "sajt": sajt,
                            "broj_izvora": broj_izvora,
                        }
                    )
            except Exception as greska:
                print(f"Upozorenje: DestinationInfoAgent nije izvrsio upit '{upit}': {greska}")

        kontekst = "\n".join(
            f"- Tema: {rezultat['upit']}\n"
            f"  Naslov: {rezultat['naziv']}\n"
            f"  Sazetak: {rezultat['opis']}\n"
            f"  Izvor: [{rezultat['broj_izvora']}] {rezultat['sajt']}"
            if rezultat["broj_izvora"] is not None
            else (
                f"- Tema: {rezultat['upit']}\n"
                f"  Naslov: {rezultat['naziv']}\n"
                f"  Sazetak: {rezultat['opis']}\n"
                "  Izvor: URL nije dostupan"
            )
            for rezultat in rezultati[:36]
        )
        prompt = (
            "Sastavi kratak, praktican putni pregled na srpskom koristeci samo informacije "
            "potkrepljene prilozenim rezultatima. Ne izmisljaj prognozu, pravila za vizu, kurs "
            "ili bezbednosna upozorenja; ako nema pouzdanih podataka, jasno napisi da nisu "
            "pronadjeni i preporuci proveru zvanicnog izvora pre puta. Razdvoji stavke: "
            "Vreme, Viza i ulazak, Valuta i kurs, Znamenitosti i aktivnosti, Bezbednost, "
            "Lokalni prevoz. Za vizu i bezbednost uzmi u obzir drzavljanstvo/pasos kada je "
            "naveden. Za prognozu navedi da je vremenska ako rezultati ne pokrivaju tacan datum. "
            "Brojeve izvora koristi u uglastim zagradama uz tvrdnje, npr. [1]. "
            "Broj mora odgovarati oznaci izvora u rezultatima. Ne izmisljaj reference "
            "i ne dodaj poseban spisak izvora; spisak ce biti dodat automatski.\n"
            f"Destinacija: {destinacija}\n"
            f"Period/duzina boravka: {period or 'nije navedeno'}\n"
            f"Drzavljanstvo/pasos: {drzavljanstvo or 'nije navedeno'}\n"
            f"Rezultati pretrage:\n{kontekst or 'Nema dostupnih rezultata.'}"
        )
        odgovor = local_llm.run(prompt, language=None)
        return self._odgovor_sa_izvorima(odgovor, izvori)
