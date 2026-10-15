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
