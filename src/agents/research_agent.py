"""Dubinsko uporedno istrazivanje modela i prodajnih ponuda."""

from __future__ import annotations


class ResearchAgent:
    """Istrazuje specifikacije, recenzije i cene za vec pronadjene proizvode."""

    def istrazi(
        self,
        web_agent,
        local_llm,
        proizvod: str,
        ponude: list[dict],
    ) -> str:
        modeli = [
            str(ponuda.get("naziv", "")).strip()
            for ponuda in ponude
            if ponuda.get("naziv")
        ]
        upiti = [
            f"{proizvod} specifications comparison reviews",
            f"{proizvod} price comparison retailers",
            f"{proizvod} independent reviews pros cons",
        ]
        upiti.extend(
            f'"{model}" specifications reviews price'
            for model in dict.fromkeys(modeli[:8])
        )

        rezultati = []
        vidjeni_urlovi = set()
        for upit in upiti:
            try:
                for rezultat in web_agent.pretrazi_dobavljace(upit):
                    sajt = str(rezultat.get("sajt", "") or "")
                    if sajt and sajt in vidjeni_urlovi:
                        continue
                    if sajt:
                        vidjeni_urlovi.add(sajt)
                    rezultati.append(
                        {
                            "upit": upit,
                            "naziv": rezultat.get("naziv", ""),
                            "opis": rezultat.get("opis", ""),
                            "sajt": sajt,
                        }
                    )
            except Exception as greska:
                print(f"Upozorenje: ResearchAgent nije izvrsio upit '{upit}': {greska}")

        ponude_za_porediti = "\n".join(
            f"- {ponuda.get('naziv', '')}: cena={ponuda.get('cena', 'nepoznato')}; "
            f"opis={ponuda.get('opis_karakteristika', '')}; "
            f"ocena={ponuda.get('ocena_i_recenzije', '')}; sajt={ponuda.get('sajt', '')}"
            for ponuda in ponude
        )
        izvori = "\n".join(
            f"- Upit: {rezultat['upit']}; naslov: {rezultat['naziv']}; "
            f"opis: {rezultat['opis']}; izvor: {rezultat['sajt']}"
            for rezultat in rezultati[:48]
        )
        prompt = (
            "Uporedi ove moguce ponude proizvoda na srpskom. Navedi modele i dostupne "
            "specifikacije u tabelarno citljivom obliku, sumiraj ocene/recenzije po izvorima, "
            "uporedi cene za isti model medju prodavnicama kada podaci to potvrdjuju, pa daj "
            "kratke prednosti, mane i preporuku. Razlikuj identicne modele od slicno nazvanih "
            "proizvoda. Ne izmisljaj podatke; oznaci nepoznato gde izvori nisu dovoljni i "
            "priloži URL-ove uz tvrdnje.\n"
            f"Trazeni proizvod: {proizvod}\n"
            f"Pronadjene ponude:\n{ponude_za_porediti}\n"
            f"Dodatni rezultati istrazivanja:\n{izvori or 'Nema dostupnih rezultata.'}"
        )
        return local_llm.run(prompt, language=None)
