import logging
import sys
from contextlib import contextmanager
from types import ModuleType

from bs4 import BeautifulSoup

from src.agents.web_agent import WebAgent


def test_contact_extractor_rejects_id_like_number_and_accepts_country_codes():
    web_agent = WebAgent()

    contacts = web_agent.izvuci_kontakt_i_cene(
        "Booking reference 73-050319623856; call +30 210 123 4567 or 0030 210 987 6543."
    )

    assert contacts["telefoni"] == [
        "+30 210 123 4567",
        "0030 210 987 6543",
    ]
    assert "73-050319623856" not in contacts["telefoni"]


def test_contact_extractor_uses_country_context_for_local_calling_code():
    web_agent = WebAgent()

    contacts = web_agent.izvuci_kontakt_i_cene(
        "Contact: 30 210 123 4567",
        zemlja="Greece",
    )

    assert contacts["telefoni"] == ["30 210 123 4567"]


def test_title_extraction_uses_only_the_first_main_heading():
    soup = BeautifulSoup(
        """
        <title>Search title • Another unrelated title</title>
        <h1>Skijatos Letovanje 2027</h1>
        <h1>YourWay najbolja ponuda letovanja</h1>
        """,
        "html.parser",
    )

    assert WebAgent._izvuci_naslov(soup) == "Skijatos Letovanje 2027"
    assert WebAgent.ocisti_naslov(
        "Skijatos Letovanje 2027 • Ostrvo sa plazama...Skijatos 2027"
    ) == "Skijatos Letovanje 2027"


def test_title_extraction_falls_back_to_first_title_element():
    soup = BeautifulSoup(
        "<title>Skijatos hoteli | Hotelske ponude</title>"
        "<title>Druga nevezana stranica</title>",
        "html.parser",
    )

    assert WebAgent._izvuci_naslov(soup) == "Skijatos hoteli"


def test_search_result_prefers_page_heading_over_joined_search_title(monkeypatch):
    class FakeDDGS:
        def text(self, _query, max_results):
            return [
                {
                    "title": "Skijatos 2027 • Letovanje...YourWay ponuda",
                    "href": "https://travel.example/skiathos",
                    "body": "Travel information for Skiathos.",
                }
            ]

    class FakeResponse:
        text = (
            "<title>Putovanja | Travel Example</title>"
            "<h1>Skijatos letovanje 2027</h1>"
            "<h1>YourWay druga ponuda</h1>"
            "<p>Travel information for Skiathos.</p>"
        )

        @staticmethod
        def raise_for_status():
            pass

    monkeypatch.setattr("src.agents.web_agent.DDGS", FakeDDGS)
    monkeypatch.setattr(
        "src.agents.web_agent.requests.get",
        lambda *_args, **_kwargs: FakeResponse(),
    )

    results = WebAgent().pretrazi_dobavljace("Skiathos")

    assert results[0]["naziv"] == "Skijatos letovanje 2027"


def test_search_skips_result_with_multiple_concatenated_prices(monkeypatch):
    class FakeDDGS:
        def text(self, _query, max_results):
            return [
                {
                    "title": (
                        "Flights to Skiathos FlightConnections "
                        "$419 Google Flights Expedia $537 ExpediaAEGEAN"
                    ),
                    "href": "https://flightconnections.com/flights-to-skiathos-jsi",
                    "body": "Flights to Skiathos.",
                }
            ]

    def unexpected_request(*_args, **_kwargs):
        raise AssertionError("A joined search result should not be loaded.")

    monkeypatch.setattr("src.agents.web_agent.DDGS", FakeDDGS)
    monkeypatch.setattr("src.agents.web_agent.requests.get", unexpected_request)

    assert WebAgent().pretrazi_dobavljace("flights to Skiathos") == []


def test_search_skips_result_with_stuck_platform_names(monkeypatch):
    class FakeDDGS:
        def text(self, _query, max_results):
            return [
                {
                    "title": "FlightConnectionsFind Cheap Flights - ExpediaAEGEAN",
                    "href": "https://flightconnections.com/flights-to-skiathos-jsi",
                    "body": "Flights to Skiathos.",
                }
            ]

    def unexpected_request(*_args, **_kwargs):
        raise AssertionError("A joined search result should not be loaded.")

    monkeypatch.setattr("src.agents.web_agent.DDGS", FakeDDGS)
    monkeypatch.setattr("src.agents.web_agent.requests.get", unexpected_request)

    assert WebAgent().pretrazi_dobavljace("flights to Skiathos") == []


def test_browser_navigation_error_returns_error_and_closes_browser(monkeypatch, caplog):
    class FakePlaywrightError(Exception):
        pass

    class FakeBrowser:
        def __init__(self):
            self.closed = False

        def new_page(self):
            return FakePage()

        def close(self):
            self.closed = True

    class FakePage:
        def goto(self, _url, timeout):
            raise FakePlaywrightError("peer closed connection without TLS close_notify")

        def wait_for_timeout(self, _timeout):
            raise AssertionError("Navigation failure should stop page processing.")

    browser = FakeBrowser()

    class FakeChromium:
        @staticmethod
        def launch(headless):
            return browser

    class FakePlaywright:
        chromium = FakeChromium()

    @contextmanager
    def fake_sync_playwright():
        yield FakePlaywright()

    playwright = ModuleType("playwright")
    sync_api = ModuleType("playwright.sync_api")
    sync_api.Error = FakePlaywrightError
    sync_api.TimeoutError = type("FakeTimeoutError", (FakePlaywrightError,), {})
    sync_api.sync_playwright = fake_sync_playwright
    playwright.sync_api = sync_api
    monkeypatch.setitem(sys.modules, "playwright", playwright)
    monkeypatch.setitem(sys.modules, "playwright.sync_api", sync_api)

    with caplog.at_level(logging.WARNING):
        rezultat = WebAgent().procitaj_sajt_sa_browserom("https://example.com")

    assert rezultat.startswith("Greska pri ucitavanju sajta:")
    assert browser.closed
    assert "peer closed connection" in caplog.text
