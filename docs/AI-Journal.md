# AI Dnevnik

## Dan 1 – Početak

Datum: 04.08.2026.

### Šta sam danas uradila

- Instalirala i pokrenula Ollama.
- Pokrenula lokalni AI model Qwen.
- Instalirala Visual Studio Code.
- Napravila projekat AI-OS.
- Kreirala foldere:
  - docs
  - src
  - data
  - tests

### Šta sam danas naučila

Danas sam napravila prve korake ka izgradnji svog AI sistema. Naučila sam kako da koristim PowerShell, Git, Ollama i Visual Studio Code.

### Moj cilj

Želim da napravim AI operativni sistem sa više AI agenata koji će:

- upravljati kalendarom
- odgovarati na e-mailove
- istraživati internet
- pronalaziti najbolje ponude
- biti povezani sa Telegramom i WhatsApp-om
- automatizovati svakodnevne poslove

### Sledeći korak

Napraviti prvog AI agenta.

## 23.9.2026.
- pytest.ini konacno radi (testovi prolaze bez greske)
- LocalLLMAgent povezan sa Ollama modelom qwen3.6:27b kroz kod (ne samo rucno)
- Dodato pravilo za dvojezicni odgovor (srpski + engleski) - radi kad je uputstvo
  u samom pitanju; system_prompt sam po sebi model ponekad ignorise kod kratkih pitanja
- Napravljen probni fajl try_agent.py za rucno testiranje agenta
- Sledece: povezati Orchestrator da koristi LocalLLMAgent umesto FakeAgent