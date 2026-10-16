"""Pretraga ponuda lokalnih i medjunarodnih turistickih agencija."""

from __future__ import annotations


class AgencyAgent:
    """Specijalizovani agent za turisticke agencije i paket-aranzmane."""

    @staticmethod
    def sastavi_upite(proizvod: str, zemlja: str, siri: bool = False) -> list[str]:
        upiti = [
            f"turisticka agencija {zemlja} aranzman {proizvod}",
            f"agencija putovanja {zemlja} organizovana putovanja {proizvod}",
            f"travel agency {zemlja} package deals {proizvod}",
            f"tour operator {zemlja} holiday package accommodation transport",
        ]
        if siri:
            upiti.extend(
                [
                    f"turisticka agencija {zemlja} letovanje paket aranzman cena",
                    f"organizovana putovanja {zemlja} turisticka agencija ponude",
                    f"tour operators offering holiday packages to {zemlja}",
                    f"vacation package {zemlja} travel company direct",
                ]
            )
        return upiti

    @staticmethod
    def pretrazi(web_agent, upit: str, zemlja: str) -> list[dict]:
        """Pokrece jedan upit za turisticke agencije."""
        return web_agent.pretrazi_dobavljace(upit, zemlja=zemlja)
