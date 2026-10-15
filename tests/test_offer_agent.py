import re

from src.agents.offer_agent import OfferAgent
from src.agents.web_agent import WebAgent


class FakeLlm:
    def __init__(self, response=""):
        self.prompts = []
        self.response = response

    def run(self, prompt, language=None):
        self.prompts.append(prompt)
        if len(self.prompts) == 1:
            return "usluga" if "letovanje" in prompt else "proizvod"
        return self.response


class FakeWebAgent:
    def __init__(self):
        self.queries = []

    def pretrazi_dobavljace(self, upit, broj_rezultata=5, zemlja=""):
        self.queries.append(upit)
        if upit.startswith("site:booking.com"):
            return [
                {
                    "naziv": "Skiathos holiday stay | Booking.com | More hotels",
                    "sajt": "https://www.booking.com/hotel/gr/example",
                    "opis": "Holiday accommodation and beach stay in Skiathos, Greece",
                    "emailovi": [],
                    "telefoni": [],
                },
                {
                    "naziv": "Cryptography research",
                    "sajt": "https://example.org/cryptography",
                    "opis": "Cryptography and computer science research",
                },
                {
                    "naziv": "Sponsored holiday",
                    "sajt": "https://googleadservices.com/aclk?url=booking.com",
                    "opis": "Holiday stay in Skiathos Greece",
                },
            ]
        if upit.startswith("site:airbnb.com"):
            return [
                {
                    "naziv": "Skiathos holiday apartment | Airbnb",
                    "sajt": "https://airbnb.com/rooms/example",
                    "opis": "JavaScript is disabled. Enable JavaScript to continue.",
                    "emailovi": [],
                    "telefoni": [],
                }
            ]
        if upit.startswith("site:tripadvisor.com"):
            return [
                {
                    "naziv": "Skiathos Greece holiday review | TripAdvisor",
                    "sajt": "https://bg.tripadvisor.com/Hotel_Review/example",
                    "opis": "Verify that you're not a robot.",
                    "emailovi": [],
                    "telefoni": [],
                }
            ]
        if "flight" in upit.lower():
            return [
                {
                    "naziv": "Flights to Skiathos | Air tickets",
                    "sajt": "https://flights.example/search?utm_source=search",
                    "opis": "Flights and air tickets to Skiathos, Greece",
                    "emailovi": ["contact@flights.example"],
                    "telefoni": [],
                }
            ]
        if "ferry" in upit.lower():
            return [
                {
                    "naziv": "Skiathos Greece holiday review",
                    "sajt": "https://es.tripadvisor.com/Hotel_Review/example",
                    "opis": "Holiday stay in Skiathos, Greece",
                    "emailovi": [],
                    "telefoni": [],
                },
                {
                    "naziv": "Skiathos ferry tickets",
                    "sajt": "https://ferry.example/tickets",
                    "opis": "Ferry tickets to Skiathos, Greece",
                },
            ]
        if "manufacturer" in upit.lower():
            return [
                {
                    "naziv": "Green coffee supplier",
                    "sajt": "https://supplier.example/green-coffee",
                    "opis": "Producer and exporter of green coffee beans",
                    "emailovi": ["sales@supplier.example"],
                },
                {
                    "naziv": "Cryptography research",
                    "sajt": "https://example.org/cryptography",
                    "opis": "Cryptography research",
                },
            ]
        return []

    def procitaj_sajt_sa_browserom(self, sajt):
        return "Live price: €149" if "airbnb.com" in sajt else "Greska: test ne ucitava stranice"

    @staticmethod
    def izvuci_kontakt_i_cene(tekst, zemlja=""):
        cene = re.findall(r"€\s?\d+", tekst)
        return {"emailovi": [], "telefoni": [], "cene": cene}


def test_service_search_filters_irrelevant_ads_and_locale_duplicates_and_finds_flights():
    offer_agent = OfferAgent()
    local_llm = FakeLlm(
        "1. Flights to Skiathos Greece\n2. Ferry tickets Skiathos Greece"
    )
    web_agent = FakeWebAgent()
    offer_agent.opisi_dobavljaca = lambda *args: {
        "zemlja": "nepoznato",
        "opis_karakteristika": "nema dovoljno informacija",
        "cena": "nepoznato",
    }

    dobavljaci = offer_agent.pronadji_dobavljace(
        web_agent,
        local_llm,
        "letovanje",
        zadata_zemlja="Greece skiathos",
        dodatni_zahtevi="avionske karte",
        kolicina="2 osobe",
    )

    assert web_agent.queries[:6] == [
        "site:booking.com letovanje Greece skiathos",
        "site:airbnb.com letovanje Greece skiathos",
        "site:tripadvisor.com letovanje Greece skiathos",
        "site:expedia.com letovanje Greece skiathos",
        "site:skyscanner.com letovanje Greece skiathos",
        "site:kayak.com letovanje Greece skiathos",
    ]
    assert "Flights to Skiathos Greece" in web_agent.queries
    assert "Ferry tickets Skiathos Greece" in web_agent.queries
    assert "letovanje Greece skiathos official website" in web_agent.queries
    assert "independent letovanje providers Greece skiathos direct contact" in web_agent.queries
    assert "letovanje Greece skiathos local providers contact" in web_agent.queries
    assert {dobavljac["kategorija_ponude"] for dobavljac in dobavljaci} == {
        "hoteli",
        "privatni_smestaj",
        "letovi",
    }
    assert next(d for d in dobavljaci if d["kategorija_ponude"] == "letovi")["naziv"] == (
        "Flights to Skiathos"
    )
    assert sum(d["kategorija_ponude"] == "hoteli" for d in dobavljaci) == 2
    assert all("cryptography" not in d["naziv"].lower() for d in dobavljaci)
    assert all("googleadservices" not in d["sajt"] for d in dobavljaci)
    assert sum("tripadvisor.com" in d["sajt"] for d in dobavljaci) == 1
    assert "€149" in next(d["cena"] for d in dobavljaci if "airbnb.com" in d["sajt"])
    letovi = next(d for d in dobavljaci if d["kategorija_ponude"] == "letovi")
    assert letovi["polaziste"] == "nepoznato"
    assert "orijentacione" in letovi["napomena_rute"]
    assert "2 osobe" in local_llm.prompts[1]


def test_product_search_filters_unrelated_results_and_uses_b2b_and_country_queries():
    offer_agent = OfferAgent()
    local_llm = FakeLlm()
    web_agent = FakeWebAgent()
    offer_agent.pronadji_direktorijume = lambda *args: ["b2b.example"]
    offer_agent.pronadji_zemlje = lambda *args: ["Brazil"]
    offer_agent.opisi_dobavljaca = lambda *args: {
        "zemlja": "Brazil",
        "opis_karakteristika": "Green coffee beans",
        "cena": "€10",
    }

    dobavljaci = offer_agent.pronadji_dobavljace(
        web_agent, local_llm, "zelena kafa"
    )

    assert web_agent.queries == [
        "site:b2b.example zelena kafa manufacturer supplier",
        "zelena kafa exporter manufacturer Brazil",
    ]
    assert len(dobavljaci) == 1
    assert dobavljaci[0]["naziv"] == "Green coffee supplier"
    assert dobavljaci[0]["zemlja_pretrage"] == "Brazil"


def test_service_search_keeps_distinct_listings_on_same_platform():
    offer_agent = OfferAgent()
    local_llm = FakeLlm("Flights to Skiathos Greece")
    web_agent = FakeWebAgent()
    web_agent.pretrazi_dobavljace = lambda query, broj_rezultata=5, zemlja="": (
        [
            {
                "naziv": "Skiathos Greece holiday review",
                "sajt": "https://bg.tripadvisor.com/Hotel_Review/one",
                "opis": "Holiday stay in Skiathos, Greece",
            },
            {
                "naziv": "Skiathos Greece holiday review",
                "sajt": "https://bg.tripadvisor.com/Hotel_Review/two",
                "opis": "Holiday stay in Skiathos, Greece",
            },
        ]
        if query.startswith("site:tripadvisor.com")
        else []
    )
    offer_agent.opisi_dobavljaca = lambda *args: {
        "zemlja": "Greece",
        "opis_karakteristika": "Skiathos holiday stay",
        "cena": "nepoznato",
    }

    dobavljaci = offer_agent.pronadji_dobavljace(
        web_agent, local_llm, "letovanje", zadata_zemlja="Greece skiathos"
    )

    assert [d["sajt"] for d in dobavljaci] == [
        "https://bg.tripadvisor.com/Hotel_Review/one",
        "https://bg.tripadvisor.com/Hotel_Review/two",
    ]


def test_rank_places_complete_and_cheaper_matching_results_first():
    offer_agent = OfferAgent()
    results = [
        {
            "naziv": "Expensive",
            "cena": "€250",
            "zemlja": "Greece",
            "emailovi": ["sales@example.com"],
            "opis_karakteristika": "Flights and beach hotel",
            "pouzdanost": "visok",
        },
        {
            "naziv": "Incomplete",
            "cena": "nepoznato",
            "zemlja": "nepoznato",
            "emailovi": [],
            "opis_karakteristika": "nema dovoljno informacija",
        },
        {
            "naziv": "Cheaper matching",
            "cena": "€125",
            "zemlja": "Greece",
            "emailovi": ["sales@cheap.example"],
            "opis_karakteristika": "Flights and beach hotel with breakfast",
            "pouzdanost": "visok",
        },
    ]

    ranked = offer_agent.rangiraj_dobavljace(results, "avionske karte, blizu plaže")

    assert [d["naziv"] for d in ranked] == ["Cheaper matching", "Expensive", "Incomplete"]


def test_title_cleanup_and_ad_redirect_detection():
    assert WebAgent.ocisti_naslov("Hotel in Skiathos | Greece hotels | Booking") == "Hotel in Skiathos"
    assert WebAgent.je_oglasni_url("https://www.google.com/aclick?url=example")
    assert WebAgent.je_oglasni_url("https://www.bing.com/ck/a?url=example")
    assert not WebAgent.je_oglasni_url("https://bing.com/travel")


def test_osnovni_domen_removes_locale_prefix_for_platforms():
    offer_agent = OfferAgent()

    assert offer_agent.osnovni_domen("https://www.booking.com/hotel/example") == "booking.com"
    assert offer_agent.osnovni_domen("https://bg.booking.com/hotel/example") == "booking.com"
    assert offer_agent.osnovni_domen("https://es.tripadvisor.com/hotel/example") == "tripadvisor.com"
    assert offer_agent.osnovni_domen("https://sk.example.com/page") == "sk.example.com"


def test_bot_protection_snippets_are_allowed_for_travel_platforms_or_destination_urls():
    offer_agent = OfferAgent()
    bot_result = {
        "naziv": "Accommodation",
        "opis": "JavaScript is disabled. Verify you're not a robot.",
        "sajt": "https://airbnb.com/rooms/123",
    }
    assert offer_agent._rezultat_povezan(
        bot_result, "vacation", "Greece Skiathos", "", "vacation Greece", "usluga"
    )

    destination_url_result = {
        **bot_result,
        "sajt": "https://local.example/stays/greece-skiathos",
    }
    assert offer_agent._rezultat_povezan(
        destination_url_result, "vacation", "Greece Skiathos", "", "vacation Greece", "usluga"
    )

    unrelated_result = {**bot_result, "sajt": "https://unrelated.example/listing"}
    assert not offer_agent._rezultat_povezan(
        unrelated_result, "vacation", "Greece Skiathos", "", "vacation Greece", "usluga"
    )


def test_service_query_builder_adds_generic_open_web_searches():
    offer_agent = OfferAgent()
    upiti = offer_agent.sastavi_upite_za_usluge(
        FakeLlm(""),
        "consulting",
        "",
        "Portugal",
    )

    assert "consulting Portugal official website" in upiti
    assert "independent consulting providers Portugal direct contact" in upiti
    assert all(not upit.startswith("site:") for upit in upiti)


def test_service_query_builder_includes_local_and_international_travel_agencies():
    offer_agent = OfferAgent()
    upiti = offer_agent.sastavi_upite_za_usluge(
        FakeLlm(""),
        "vacation",
        "half board",
        "Portugal Madeira",
    )

    assert "turisticka agencija Portugal Madeira aranzman vacation" in upiti
    assert "travel agency Portugal Madeira package deals vacation" in upiti


def test_service_search_runs_fallback_queries_and_keeps_all_eight_plus_results():
    offer_agent = OfferAgent()
    local_llm = FakeLlm("Flights to Skiathos Greece")
    web_agent = FakeWebAgent()

    def search(upit, broj_rezultata=5, zemlja=""):
        web_agent.queries.append(upit)
        if "local providers contact" in upit:
            return [
                {
                    "naziv": f"Skiathos vacation hotel {index}",
                    "sajt": f"https://stay{index}.example/greece-skiathos/{index}",
                    "opis": "Vacation hotel in Greece Skiathos",
                }
                for index in range(9)
            ]
        return []

    web_agent.pretrazi_dobavljace = search
    offer_agent.opisi_dobavljaca = lambda *args: {
        "zemlja": "Greece",
        "opis_karakteristika": "Vacation hotel",
        "cena": "nepoznato",
    }

    dobavljaci = offer_agent.pronadji_dobavljace(
        web_agent, local_llm, "letovanje", zadata_zemlja="Greece Skiathos"
    )

    assert len(dobavljaci) == 9
    assert "letovanje Greece Skiathos local providers contact" in web_agent.queries


def test_service_search_extracts_rating_and_review_details_from_loaded_page():
    offer_agent = OfferAgent()
    local_llm = FakeLlm("")
    web_agent = FakeWebAgent()
    web_agent.pretrazi_dobavljace = lambda upit, broj_rezultata=5, zemlja="": (
        [
            {
                "naziv": "Skiathos vacation hotel",
                "sajt": "https://hotel.example/skiathos",
                "opis": "Vacation hotel in Skiathos, Greece",
            }
        ]
        if "official website" in upit
        else []
    )
    web_agent.procitaj_sajt_sa_browserom = lambda _sajt: (
        "Guest rating 9.2/10 based on 127 reviews. "
        'Guest reviews: "Wonderful location and friendly staff."'
    )
    offer_agent.opisi_dobavljaca = lambda *args: {
        "zemlja": "Greece",
        "opis_karakteristika": "Vacation hotel",
        "cena": "nepoznato",
    }

    dobavljaci = offer_agent.pronadji_dobavljace(
        web_agent, local_llm, "letovanje", zadata_zemlja="Greece Skiathos"
    )

    assert len(dobavljaci) == 1
    assert "9.2/10" in dobavljaci[0]["ocena_i_recenzije"]
    assert "127" in dobavljaci[0]["ocena_i_recenzije"]
    assert "Wonderful location and friendly staff" in dobavljaci[0]["ocena_i_recenzije"]


def test_flight_queries_include_comparison_sites_and_airline_searches():
    offer_agent = OfferAgent()
    upiti = offer_agent.sastavi_upite_za_usluge(
        FakeLlm(""),
        "vacation",
        "flight tickets",
        "Greece Skiathos",
    )

    assert "site:skyscanner.com flights to Greece Skiathos" in upiti
    assert "site:google.com/travel/flights flights to Greece Skiathos" in upiti
    assert "site:kayak.com flights to Greece Skiathos" in upiti
    assert "site:momondo.com flights to Greece Skiathos" in upiti
    assert "site:kiwi.com flights to Greece Skiathos" in upiti
    assert "flights to Greece Skiathos airline" in upiti
    assert any(
        query.startswith("direct flights Greece Skiathos ")
        for query in upiti
    )


def test_flight_queries_include_origin_and_local_language_for_serbian_origins():
    offer_agent = OfferAgent()
    upiti = offer_agent.sastavi_upite_za_usluge(
        FakeLlm(""),
        "vacation",
        "flight tickets",
        "Greece Skiathos",
        polaziste="Belgrade",
    )

    assert "site:skyscanner.com flights from Belgrade to Greece Skiathos" in upiti
    assert "site:kayak.com flights from Belgrade to Greece Skiathos" in upiti
    assert "Belgrade to Greece Skiathos flight tickets" in upiti
    assert "avionska karta Belgrade Greece Skiathos" in upiti
    assert "letovi iz Belgrade za Greece Skiathos" in upiti


def test_flight_details_extract_airline_and_stop_type():
    offer_agent = OfferAgent()
    details = offer_agent._izvuci_podatke_o_letu(
        {
            "naziv": "Skiathos flight results",
            "zemlja_pretrage": "Greece Skiathos",
        },
        "Aegean Airlines flight from Athens to Skiathos with 1 stop €189",
    )

    assert details == {
        "avio_kompanija": "Aegean Airlines",
        "tip_leta": "Let sa presedanjem",
        "cena_karte": "€189",
    }


def test_flight_company_is_not_guessed_without_route_and_fare_context():
    offer_agent = OfferAgent()

    details = offer_agent._izvuci_podatke_o_letu(
        {"naziv": "Flights to Skiathos", "zemlja_pretrage": "Greece Skiathos"},
        "LATAM Airlines serves routes in South America. "
        "A flight to Skiathos is available from €189.",
    )

    assert "avio_kompanija" not in details


def test_booking_language_urls_normalize_to_english_and_keep_distinct_properties():
    offer_agent = OfferAgent()

    assert offer_agent._normalizuj_url_rezultata(
        "https://www.booking.com/hotel/gr/example.sr.html"
    ) == "https://www.booking.com/hotel/gr/example.en-gb.html"
    assert offer_agent._normalizuj_url_rezultata(
        "https://www.booking.com/hotel/gr/example.en-us.html"
    ) == "https://www.booking.com/hotel/gr/example.en-gb.html"
    assert offer_agent._normalizuj_url_rezultata(
        "https://www.booking.com/hotel/gr/another-hotel.sl.html"
    ) != offer_agent._normalizuj_url_rezultata(
        "https://www.booking.com/hotel/gr/example.sr.html"
    )

    assert offer_agent._kljuc_rezultata(
        "https://www.booking.com/hotel/gr/example.sr.html?label=one"
    ) == offer_agent._kljuc_rezultata(
        "https://www.booking.com/hotel/gr/example.sl.html?label=two"
    )


def test_travel_agency_filter_keeps_package_agency_not_local_guide_listing():
    offer_agent = OfferAgent()
    upit = "travel agency Greece package deals vacation"
    assert offer_agent._rezultat_povezan(
        {
            "naziv": "Island Travel - Holiday Packages",
            "opis": "Travel agency offering holiday packages in Greece.",
            "sajt": "https://islandtravel.example/packages",
        },
        "vacation",
        "Greece Skiathos",
        "",
        upit,
        "usluga",
        "agencije_medjunarodne",
    )
    assert not offer_agent._rezultat_povezan(
        {
            "naziv": "Private Local Guides & Tours",
            "opis": "Local guides and walking tours in Greece.",
            "sajt": "https://localguide.example/tours",
        },
        "vacation",
        "Greece Skiathos",
        "",
        upit,
        "usluga",
        "agencije_medjunarodne",
    )


def test_service_search_deduplicates_booking_locales_after_url_normalization():
    offer_agent = OfferAgent()
    offer_agent.odredi_tip_potrage = lambda *args: "usluga"
    web_agent = FakeWebAgent()

    def search(upit, broj_rezultata=5, zemlja=""):
        web_agent.queries.append(upit)
        if upit.startswith("site:booking.com"):
            return [
                {
                    "naziv": "10 najboljih hotelov v mestu Skiathos",
                    "sajt": "https://www.booking.com/hotel/gr/example.sr.html?label=serbian",
                    "opis": "Hotel accommodation in Skiathos, Greece",
                },
                {
                    "naziv": "10 najboljih hotelov v mestu Skiathos",
                    "sajt": "https://www.booking.com/hotel/gr/example.sl.html?label=slovenian",
                    "opis": "Hotel accommodation in Skiathos, Greece",
                },
                {
                    "naziv": "Another Skiathos hotel",
                    "sajt": "https://www.booking.com/hotel/gr/other.sr.html",
                    "opis": "Hotel accommodation in Skiathos, Greece",
                },
            ]
        return []

    web_agent.pretrazi_dobavljace = search
    offer_agent.opisi_dobavljaca = lambda *args: {
        "zemlja": "Greece",
        "opis_karakteristika": "Hotel",
        "cena": "nepoznato",
    }

    ponude = offer_agent.pronadji_dobavljace(
        web_agent, FakeLlm(""), "vacation", "Greece Skiathos"
    )

    booking_ponude = [d for d in ponude if "booking.com" in d["sajt"]]
    assert len(booking_ponude) == 2
    assert all(".en-gb.html" in d["sajt"] for d in booking_ponude)


def test_service_search_preserves_results_for_each_offer_category():
    offer_agent = OfferAgent()
    offer_agent.odredi_tip_potrage = lambda *args: "usluga"
    web_agent = FakeWebAgent()

    def result(naziv, domen, opis, path):
        return {"naziv": naziv, "sajt": f"https://{domen}/{path}", "opis": opis}

    def search(upit, broj_rezultata=5, zemlja=""):
        web_agent.queries.append(upit)
        if upit.startswith("site:booking.com"):
            return [
                result("Skiathos Hotel One", "hotel-one.example", "Hotel in Greece Skiathos", "stay"),
                result("Skiathos Hotel Two", "hotel-two.example", "Hotel in Greece Skiathos", "stay"),
            ]
        if upit.startswith("site:airbnb.com"):
            return [
                result("Skiathos private apartment", "host-one.example", "Private apartment in Greece Skiathos", "one"),
                result("Skiathos private villa", "host-two.example", "Private villa accommodation in Greece Skiathos", "two"),
            ]
        if upit.startswith("turisticka agencija"):
            return [
                result("Jadran Turisticka Agencija Aranzmani", "jadran.example", "Turisticka agencija offers aranzmani in Greece Skiathos", "aranzmani"),
                result("Adria Turisticka Agencija", "adria.example", "Turisticka agencija with organized holiday packages in Greece Skiathos", "packages"),
            ]
        if upit.startswith("travel agency"):
            return [
                result("Global Travel Agency Packages", "globaltravel.example", "Travel agency holiday packages in Greece Skiathos", "packages"),
                result("World Travel Agency", "worldtravel.example", "Travel agency with holiday packages in Greece Skiathos", "holidays"),
            ]
        if upit.startswith("site:skyscanner.com"):
            return [
                result("Skyscanner flights to Skiathos", "skyscanner.com", "Flights from Athens to Skiathos Greece", "routes")
            ]
        if upit.startswith("site:kayak.com"):
            return [
                result("Kayak flights to Skiathos", "kayak.com", "Flights from Athens to Skiathos Greece", "routes")
            ]
        if upit.startswith('"Aegean Airways" official website'):
            return [
                result("Aegean Airways official flights", "aegean.example", "Flights from Athens to Skiathos Greece", "flights")
            ]
        return []

    class AirlineLlm(FakeLlm):
        def run(self, prompt, language=None):
            self.prompts.append(prompt)
            if "Iz sledecih rezultata pretrage izdvoj" in prompt:
                return "Airline: Aegean Airways"
            return ""

    web_agent.pretrazi_dobavljace = search
    web_agent.procitaj_sajt_sa_browserom = lambda _sajt: "Greska: no page"
    offer_agent.opisi_dobavljaca = lambda *args: {
        "zemlja": "Greece",
        "opis_karakteristika": "Travel offer",
        "cena": "nepoznato",
    }

    ponude = offer_agent.pronadji_dobavljace(
        web_agent,
        AirlineLlm(""),
        "vacation",
        "Greece Skiathos",
        dodatni_zahtevi="flight tickets",
    )

    kategorije = {d["kategorija_ponude"] for d in ponude}
    assert {
        "hoteli",
        "privatni_smestaj",
        "agencije_lokalne",
        "agencije_medjunarodne",
        "letovi",
    } <= kategorije
    assert len([d for d in ponude if d["kategorija_ponude"] == "hoteli"]) >= 2
    assert len([d for d in ponude if d["kategorija_ponude"] == "privatni_smestaj"]) >= 2
    assert len([d for d in ponude if d["kategorija_ponude"] == "agencije_lokalne"]) >= 2
    assert len([d for d in ponude if d["kategorija_ponude"] == "agencije_medjunarodne"]) >= 2
    flight_results = [d for d in ponude if d["kategorija_ponude"] == "letovi"]
    assert len(flight_results) >= 3
    flight_domains = {offer_agent.osnovni_domen(d["sajt"]) for d in flight_results}
    assert "skyscanner.com" in flight_domains
    assert "kayak.com" in flight_domains
    assert "aegean.example" in flight_domains
    assert all(
        "airbnb.com" not in d["sajt"] and "booking.com" not in d["sajt"]
        for d in ponude
        if d["kategorija_ponude"].startswith("agencije_")
    )
