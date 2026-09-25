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

## 25.9.2026.
- Napravljen main.py - prvi put ceo lanac TI -> Orchestrator -> LocalLLMAgent -> Ollama -> TI radi
- Otkriven problem: model qwen3.6:27b se delimicno preliva na CPU (82% GPU / 18% CPU),
  zbog cega odgovori traju 1-3 minuta. Verovatno zbog velicine modela (17GB) u odnosu
  na VRAM graficke (16GB). Timeout povecan na 180 sekundi kao privremeno resenje.
- Optimizacija brzine (manji model ili GPU podesavanje) ostavljena za kasnije
- Sledece: pametno rutiranje - Orchestrator sam bira agenta na osnovu zadatka

## 25.9.2026. (nastavak)
- Dodato pametno rutiranje u Orchestrator (route_task) - sam bira agenta
  na osnovu kljucnih reci u zadatku (fajl/dokument -> FileAgent, ostalo -> LocalLLMAgent)
- Napravljen FileAgent - cita tekstualne fajlove i vraca sadrzaj
- main.py azuriran da koristi orchestrator.run() umesto rucnog run_task()
- Testirano: FileAgent i LocalLLMAgent rade ispravno, rutiranje bira pravog agenta
- Resen problem sa dvojezicnoscu - dodato uputstvo direktno u svaki prompt u kodu
  (ne oslanjamo se samo na system_prompt, koji model ponekad ignorise)
- Resen problem sa timeout-om za kompleksna pitanja - timeout povecan na 600 sekundi (10 min)
- Probano i odbaceno: manji model (qwen3:30b-a3b) i smanjenje num_ctx - nijedno
  nije znacajno ubrzalo rad, GPU/CPU odnos ostaje ~80/20 nezavisno od ovih izmena
- Odluka: za sada zadrzavamo jak model (qwen3.6:27b) i duzi timeout, umesto
  brzine. Kompleksna pitanja traju 1-5 minuta ali daju kvalitetan odgovor
- Buduci plan: dodati cloud_agent (Claude/GPT API) za najteze zadatke, kad
  zatreba brzina ili jos veci kvalitet - procenjena cena 5-30E mesecno za
  umerenu upotrebu
- Sledece: napraviti web_agent (pretraga interneta), pa test za rutiranje