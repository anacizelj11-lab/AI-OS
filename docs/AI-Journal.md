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

## 28.9.2026.

- Instalirala biblioteku `ddgs` (DuckDuckGo Search) za pretragu interneta bez potrebe za API kljucem.
- Napravljen novi agent `WebAgent` (src/agents/web_agent.py) koji pretrazuje internet i vraca top rezultate (naslov, kratak opis, link).
- WebAgent registrovan u main.py i ukljucen u automatsko rutiranje (Orchestrator prepoznaje reci kao "pretrazi", "internet", "sajt", "pronadji online" i salje zadatak na web_agent).
- Testirano: pretraga cene bitkoina vratila je tacne, aktuelne rezultate sa vise sajtova (coingecko, cex.io...).
- Testirano rutiranje izmedju sva tri agenta (file_agent, web_agent, local_llm) - Orchestrator ispravno prepoznaje kom agentu treba da posalje zadatak.
- Napomena: WebAgent i FileAgent ne prolaze kroz model, pa njihovi odgovori nisu dvojezicni (to je ocekivano, ne greska) - dvojezicnost vazi samo za LocalLLMAgent.
- Ispravljen problem sa sporim odgovorima posle perioda neaktivnosti - dodat `keep_alive: "30m"` u LocalLLMAgent, sto drzi model ucitan u memoriji 30 minuta posle svakog poziva, umesto da se odmah izbaci iz memorije.
- Razmotrena ideja da WebAgent prosledjuje rezultate pretrage kroz LocalLLMAgent radi dvojezicnog sazetka - odluceno da se za sada ostave sirovi rezultati (tacnije i brze za cinjenice/brojeve kao sto su cene), a sazimanje ostaviti za kasnije, za istrazivacke zadatke gde je to korisnije.

## 29.9.2026.

- Dodata AI podrska za sastavljanje email-a: umesto rucnog kucanja, AI (lokalni model) sada moze da napise nacrt teksta na osnovu kratkog opisa.
- Dodata mogucnost izbora jezika (srpski / engleski / oba) za AI predlog teksta.
- Ispravljeno vise problema: AI vise ne odgovara kao da je on primalac poruke, vec pise email u ime korisnika; ne menja pravopis imena i prezimena; ne dodaje markdown formatiranje; ne prelama recenice usred reda; ima ispravnu strukturu (pozdrav, tekst, zavrsni pozdrav, potpis).
- Testirano slanje pravog email-a - uspesno.
- Sledeci koraci: mogucnost rucne izmene AI predloga pre slanja, pregled mogucnosti web_agent-a za istrazivanje i izvestaje.

## 1.10.2026.

- Nadogradjena Ollama verzija (0.34.4 -> 0.35.0).
- Preuzet novi lokalni model mistral-small (24B) i podesen kao podrazumevani model u LocalLLMAgent-u, umesto qwen3.6:27b - cilj: manje izmisljenih reci/fraza u srpskom tekstu i brzi odgovori.
- Dodata opcija "izmeni" pri slanju email-a: pored da/ne, sada moze da se zatrazi ispravka AI predloga teksta (npr. "ukloni poslednju recenicu", "promeni pozdrav") - ispravka se saljе nazad kroz AI zajedno sa prethodnim nacrtom, umesto da se trazi rucno pisanje celog teksta.
- Testirano: mistral-small daje znatno bolji, gramaticki ispravniji tekst na srpskom nego qwen3.6:27b. "Izmeni" opcija radi ispravno kada je instrukcija konkretna i jasna (npr. "obrisi poslednji pasus") - kod opstijih instrukcija AI ne pogodi uvek tacno sta treba da promeni.
- Obrisani stari modeli (qwen3.6:27b, qwen3:30b-a3b) radi oslobadjanja prostora na disku, nakon potvrde da mistral-small radi dobro.
- Testirano slanje pravog email-a sa izmenjenim nacrtom - uspesno.
- Sledeci koraci: dalje doterivanje "izmeni" opcije (konkretnije instrukcije daju bolje rezultate); mogucnost da agent cita primljeni email i sastavi odgovor na osnovu njegovog sadrzaja i korisnikovih instrukcija; pregled mogucnosti web_agent-a za istrazivanje i izvestaje.

## 5.10.2026.

Danas smo radili na "istrazi" komandi (dubinsko istrazivanje preko interneta):
- Dodata nova komanda "istrazi" u main.py koja koristi WebAgent + lokalni AI da napravi izvestaj o nekoj temi
- Prosirena da radi vise pretraga odjednom umesto samo jedne
- AI sada sam smislja pametne upite za pretragu na osnovu pitanja, umesto fiksne seme
- Dodato pravilo da se automatski bira jezik pretrage (srpski za Srbiju, engleski za svet/globalne teme) za bolje rezultate
- Zakljucak: pretraga sada daje mnogo bolje rezultate sa stvarnim brojevima i izvorima, ali konkretni kontakti kompanija/dobavljaca se i dalje retko nalaze na internetu - za to ce biti potrebno direktno slanje email upita dobavljacima (sledeci veliki korak)

Sledeci koraci: probati slanje email upita dobavljacu za konkretnu ponudu.

## 6.10.2026.

Danas smo radili na EmailAgent-u i novom OfferAgent-u:
- Dodata mogucnost EmailAgent-u da cita pristigle mejlove sa posebnom Gmail oznakom "Ponude-AIOS" (read-only, bezbedno ogranicen pristup)
- Napravljen nov agent: OfferAgent - trazi dobavljace preko WebAgent-a, sastavlja upit za ponudu preko lokalnog AI-a, poredi pristigle ponude i cuva istoriju u memory.json
- Registrovan OfferAgent u main.py
- Greska: offer_agent.py je slucajno napravljen u pogresnom folderu, sto je izazvalo ModuleNotFoundError pri pokretanju

## 7.10.2026.

Nastavljeno sa OfferAgent-om, veliki napredak ali i otkriveno nekoliko stvarnih problema:
- Ispravljena lokacija fajla offer_agent.py - program se pokrece bez greske
- Dodata nova komanda "trazi ponudu" u main.py sa celim tokom: trazenje dobavljaca, slanje upita, citanje odgovora, poredjenje ponuda, cuvanje istorije
- Dodata funkcija WebAgent-u (pretrazi_dobavljace) koja sama pretrazuje internet, ulazi na svaki sajt i izvlaci email/telefon/sadrzaj - automatski, bez rucnog unosa email-a
- OfferAgent sada koristi stvarni sadrzaj sajta dobavljaca (ne samo kratak opis iz pretrage) da sastavi prilagodjen email
- Dodato da OfferAgent pravi vise razlicitih upita za pretragu (kao kod "istrazi") i sam bira jezik (srpski/engleski) prema temi
- Testirano uzivo nekoliko puta - svaki put popravljena po jedna greska (dupli manuelni unos email-a, pogresan jezik pretrage, upit koji ne koristi pravi sadrzaj sajta)

Otkriveni problemi koji ostaju za sledeci put:
- Opsta internet pretraga uglavnom nalazi prodavnice/posrednike, ne prave proizvodjace/uzgajivace - treba pretrazivati specijalizovane B2B direktorijume (Alibaba, Made-in-China, ThomasNet, Europages i slicno) umesto opsteg interneta
- Bag: posle "trazi ponudu" kad se svi dobavljaci odbiju, komanda "kraj" ne gasi program kako treba - treba istraziti
- Povremeno se u predlogu email-a pojavljuje dupli tekst (srpski pa engleski) - jezik treba doraditi

Dogovoreno: ne prelazimo na sledeci projekat (npr. BookAgent) dok OfferAgent ne pronalazi prave proizvodjace/uzgajivace kako treba.