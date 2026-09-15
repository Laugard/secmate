# Project specification – SecMate

## 1. Formål

SecMate er en fælles, lokal-first AI-assistent i Discord for en IT-sikkerhedsstudiegruppe. Den skal hjælpe med læring, research, motivation og praktisk planlægning uden betaling pr. AI-kald. Systemet hostes på én gruppemedlems computer og bruges af mindst to personer gennem samme Discord-bot og samme database.

## 2. Succeskriterium for MVP

MVP er færdig, når gruppen kan demonstrere følgende i én Discord-server:

1. To personer kan bruge den samme bot.
2. `/ask` svarer på et fagligt spørgsmål med belæg fra mindst én PDF, gruppen ikke selv har skrevet, og viser filnavn + side.
3. `/remember` gemmer en ufølsom fælles oplysning i SQLite, og `/memories` viser den efter bot-genstart.
4. En deadline kan oprettes og vises deterministisk.
5. Botten sender én daglig, proaktiv digest til en konfigureret kanal og undgår dubletter efter genstart.
6. `/health` viser forståeligt, om Discord, database, Ollama, modeller og dokumentindeks er klar.
7. Ingen betalt/cloud AI-tjeneste anvendes.

Nyhedsmodulet er næste prioritet og skal være med i den komplette version, men ovenstående er demoens sikre minimum.

## 3. Brugere og roller

| Rolle | Må |
|---|---|
| Studerende | `/ask`, `/assistant`, `/remember`, `/memories`, `/deadlines list`, `/today`, `/news latest`, `/health` |
| Admin (`Manage Guild` eller adminrolle) | Alle ovenstående samt sletning, deadline-ændringer, manuel feed-kørsel, reindex og cleanup |
| Host-ansvarlig | Installere Ollama/Python, beskytte `.env`, køre processen, tage backup og håndtere tokenrotation |

Ingen brugerprofiler eller individuelle progress-data er nødvendige i MVP.

## 4. Slash commands

### `/ask question`

- Input: spørgsmål på højst `MAX_PROMPT_CHARS`.
- Bot deferrer interaction straks.
- Spørgsmålet embeddes lokalt.
- De mest relevante dokumentchunks findes i SQLite.
- Qwen får kun spørgsmålet, stramme systeminstruktioner og de hentede chunks.
- Output er dansk som standard og indeholder inline-kilder som `[filnavn, side 3]`.
- Hvis retrieval ikke giver relevant belæg, må modellen ikke opfinde et svar. Den skal sige, at dokumenterne ikke giver tilstrækkeligt belæg.
- Prompts/svar gemmes ikke.

### `/assistant request`

En kontrolleret agentisk kommando. Modellen må vælge mellem følgende read-only tools:

- `search_documents(query)`
- `list_deadlines(days_ahead)`
- `list_memories()`
- `latest_news(category, limit)`

Regler:

- højst 4 modelrunder
- ingen tool, der skriver data
- ingen shell, fri filadgang eller vilkårlig URL
- toolargumenter valideres
- resultat skal vise kilder, når dokumenter/nyheder bruges
- ved toolfejl gives et delvist svar med tydelig status

Eksempel: “Hvad skal vi nå denne uge, og hvordan hænger det sammen med vores materiale om NIS2?”

### `/remember text`

- Gemmer en fælles, ufølsom note på højst `MAX_MEMORY_CHARS`.
- Bot viser før lagring: “Gem ikke persondata, adgangskoder eller private oplysninger.”
- Der gemmes ikke forfatter-ID eller brugernavn.
- Standardudløb: `MEMORY_RETENTION_DAYS`.
- Returnerer et kort, ikke-sekventielt offentligt ID til senere sletning.

### `/memories`

- Viser aktive fælles noter for serveren.
- Ingen LLM nødvendig.

### `/forget memory_id`

- Admin-only.
- Sletter én note og tilhørende data permanent.

### `/deadlines add title due_date due_time`

- Admin-only.
- `due_date`: obligatorisk ISO-format `YYYY-MM-DD`.
- `due_time`: valgfri `HH:MM`, ellers 23:59 lokal tid.
- Ingen AI-datofortolkning.
- Titel højst 120 tegn.

### `/deadlines list`

- Viser kommende deadlines sorteret nærmest først.
- Viser dansk lokaltid og antal dage/timer.
- Ingen LLM nødvendig.

### `/deadlines complete deadline_id` og `/deadlines delete deadline_id`

- Admin-only.
- Complete markerer afsluttet; cleanup sletter efter retention-perioden.
- Delete sletter straks.

### `/today`

- Viser deadlines de næste 7 dage, et studie-fokus og ét quizspørgsmål baseret på dokumentindekset.
- Hvis Ollama er nede, vises deadlines stadig og quizdelen markeres utilgængelig.

### `/news latest category`

- Viser allerede hentede nyheder fra SQLite.
- Kategori: `sårbarheder`, `cyberangreb`, `ai-security`, `lovgivning`, `andet` eller `alle`.
- Hvert item viser titel, kort dansk resumé, kilde, original URL, udgivelsesdato og hentetid.

### `/news refresh`

- Admin-only.
- Henter konfigurerede feeds, deduplikerer, klassificerer/resumerer lokalt og poster nye items til mappede kanaler.
- Vilkårlige bruger-URL'er accepteres ikke.

### `/reindex`

- Admin-only.
- Indekserer tilladte `.pdf`, `.md` og `.txt` fra `data/documents/`.
- Viser antal dokumenter, sider/chunks, ignorerede filer og fejl.
- Genindeksering er idempotent via SHA-256 af filindhold + embedmodel.

### `/health`

- Viser grøn/gul/rød for: database, Ollama API, chatmodel, embeddingmodel, dokumentchunks, digest-kanal og nyhedskanaler.
- Viser aldrig token, stier med brugerens hjemmemappe eller rå exceptions.

## 5. Automatisk adfærd

### Daglig digest

- Check-loop kører hvert minut.
- Når lokal tid passerer `DAILY_DIGEST_TIME`, forsøger botten at claim'e dagens digest atomisk i SQLite.
- Kun vinderen sender; bot-genstart må ikke give en ekstra besked.
- Indhold: kommende deadlines, ét kildebaseret quizspørgsmål og kort fokus.
- Ingen digest sendes, hvis kanal-ID mangler; der logges en konfigurationsadvarsel.

### Daglig nyhedsopdatering

- Samme mønster ved `DAILY_NEWS_TIME`.
- Kun nye, deduplikerede items postes.
- Maks. `NEWS_MAX_ITEMS_PER_RUN` pr. kørsel.
- Fejl i ét feed må ikke stoppe andre feeds eller botten.

### Cleanup og backup

- Cleanup én gang dagligt efter retention-regler.
- SQLite online backup én gang dagligt.
- Behold 7 seneste backups.
- Backup indeholder ikke `.env`, logs eller dokumentfiler.

## 6. Dokument-RAG

### Understøttede filer

- PDF med maskinlæsbar tekst
- UTF-8 Markdown
- UTF-8 tekst

Scannede billed-PDF'er/OCR er ude af scope. Indeksering skal opdage en PDF uden tilstrækkelig tekst og give en tydelig fejl.

### Pipeline

1. Validér extension, filstørrelse, sideantal og sti under dokumentmappen.
2. Beregn SHA-256.
3. Udtræk tekst side for side; bevar sidehenvisning.
4. Normalisér whitespace uden at ødelægge sætninger.
5. Chunk omkring `RAG_CHUNK_CHARS` med overlap.
6. Batch-embed chunks via `embeddinggemma`.
7. Gem metadata, tekst og float32-vector som BLOB i SQLite i én transaktion.
8. Ved query: embed spørgsmålet med samme model, brug cosine/dot product, vælg top-K og filtrér på minimumsscore.
9. Send kun de valgte chunks til chatmodellen.

Ollamas embed-endpoint returnerer normaliserede vektorer. Implementationen skal stadig kontrollere dimension og afvise indeks/query med forskellige embedmodeller.

## 7. Nyhedsbehandling

Input er kun titel, feed-summary, link, kilde og dato fra allowlistede RSS/Atom-feeds. MVP downloader ikke tilfældige artikelsider.

Modellen skal returnere valideret JSON/structured output:

```json
{
  "category": "sårbarheder",
  "summary_da": "Kort faktuelt resumé på højst 450 tegn.",
  "study_relevance_da": "Hvorfor dette er relevant for IT-sikkerhedsstudiet.",
  "confidence": 0.82
}
```

Ved ugyldigt output forsøges én reparationsrunde. Derefter bruges kategori `andet`, original titel og et neutralt fallback-resumé. AI-resumé mærkes som resumé; originalkilden linkes altid.

## 8. Ikke-funktionelle krav

- Normal slash command skal enten deferre eller svare hurtigt nok til Discord-interaction.
- Én langsom Ollama-request må ikke blokere andre ikke-AI-kommandoer.
- Modelkald har timeout og bruger semaphore med maksimal concurrency 1 som standard.
- Databaseændringer er transaktionelle og bruger WAL-mode, foreign keys og busy timeout.
- Botten starter med tydelig konfigurationsvalidering.
- Funktioner uden AI (`/deadlines list`, `/memories`, grundlæggende health) virker, selv når Ollama er nede.
- Alle brugerfejl gives på dansk og uden stack trace.
- Kode og tests skal virke på macOS, Windows og Linux med Python 3.12.
- Automated tests kræver ikke Discord-token, internet eller en kørende Ollama.

## 9. Ude af scope

- hjemmeside, login, mobilapp eller OpenWebUI
- cloud-hosting eller 24/7-garanti
- betalte AI-API'er
- Discord-DM'er
- lagring af samtalehistorik
- individuelle elevprofiler eller karaktertracking
- OCR, lyd, billeder eller video
- automatisk webcrawl/search
- arbitrary URL ingestion
- finetuning af model
- avanceret vector database
- automatisk ændring/sletning via agentens tool calling

## 10. Definition of Done

Projektet er kun færdigt, når alle Must-tests i `ACCEPTANCE_TESTS.md` er bestået, README kan følges på en ren maskine, `.env`/runtime-data ikke er tracket, og to gruppemedlemmer har udført samme live setup-test.

