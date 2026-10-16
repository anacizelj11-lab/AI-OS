from src.agents.destination_info_agent import DestinationInfoAgent


class FakeWebAgent:
    def __init__(self):
        self.queries = []

    def pretrazi_dobavljace(self, upit, zemlja=""):
        self.queries.append((upit, zemlja))
        return [
            {
                "naziv": "Official travel information",
                "opis": "Destination travel details",
                "sajt": "https://travel.example",
            }
        ]


class FakeLlm:
    def __init__(self):
        self.prompts = []

    def run(self, prompt, language=None):
        self.prompts.append(prompt)
        return "Pregled destinacije"


def test_destination_info_includes_citizenship_in_queries_and_summary():
    agent = DestinationInfoAgent()
    web_agent = FakeWebAgent()
    local_llm = FakeLlm()

    pregled = agent.istrazi(
        web_agent,
        local_llm,
        "Greece Skiathos",
        period="June 20, 15 days",
        drzavljanstvo="Serbian",
    )

    assert pregled == "Pregled destinacije"
    assert any("Serbian passport visa entry requirements" in query for query, _ in web_agent.queries)
    assert any("Serbian passport travel advisory safety" in query for query, _ in web_agent.queries)
    assert "Drzavljanstvo/pasos: Serbian" in local_llm.prompts[0]
    assert "Period/duzina boravka: June 20, 15 days" in local_llm.prompts[0]


def test_destination_info_works_without_citizenship():
    agent = DestinationInfoAgent()
    web_agent = FakeWebAgent()
    local_llm = FakeLlm()

    pregled = agent.istrazi(
        web_agent,
        local_llm,
        "Portugal",
        period="one week in July",
    )

    assert pregled == "Pregled destinacije"
    assert any("visa entry requirements Portugal" in query for query, _ in web_agent.queries)
    assert any("travel advisory safety Portugal" in query for query, _ in web_agent.queries)
    assert "Drzavljanstvo/pasos: nije navedeno" in local_llm.prompts[0]


def test_destination_info_adds_matching_source_links_for_citations():
    class CitedWebAgent(FakeWebAgent):
        def pretrazi_dobavljace(self, upit, zemlja=""):
            self.queries.append((upit, zemlja))
            return [
                {
                    "naziv": "Official tourism board",
                    "opis": "Destination information",
                    "sajt": "https://tourism.example/info",
                },
                {
                    "naziv": "Weather service",
                    "opis": "Forecast information",
                    "sajt": "https://weather.example/forecast",
                },
            ]

    class CitedLlm(FakeLlm):
        def run(self, prompt, language=None):
            self.prompts.append(prompt)
            return "Vreme [2], a turisticke informacije [1]. Nepoznata referenca [99]."

    pregled = DestinationInfoAgent().istrazi(
        CitedWebAgent(),
        CitedLlm(),
        "Greece Skiathos",
    )

    assert "Vreme [2], a turisticke informacije [1]. Nepoznata referenca ." in pregled
    assert "Izvori:\n[1] Official tourism board — https://tourism.example/info" in pregled
    assert "[2] Weather service — https://weather.example/forecast" in pregled
    assert "[99]" not in pregled
