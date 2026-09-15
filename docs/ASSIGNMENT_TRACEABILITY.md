# Sporbarhed til opgavekrav

Denne fil viser, hvor systemet opfylder kravene. De tre slides og diagrammer skal gruppen stadig lave og formulere selv.

## 1. Minimumsfunktionalitet

| Opgavekrav | SecMate-løsning | Evidens |
|---|---|---|
| Mindst én kilde, I ikke selv har skrevet | Lokal PDF/MD/TXT indekseres; `/ask` citerer fil + side | L-02, ingestionrapport, valgt PDF |
| Husker mindst én ting mellem to brug | `/remember` gemmer fælles note i SQLite | L-03 før/efter genstart |
| Mindst to bruger samme opsætning | Én host, én bot, én DB; to Discord-brugere | L-01 |

## 2. Ønskede fire områder

| Område | Funktioner |
|---|---|
| Læring | `/ask`, kildebaserede svar, quiz i `/today`/digest |
| Research | dokument-RAG, sikkerhedsnyheder med original kilde, `/assistant` |
| Motivation | daglig quiz/fokus uden brugerprompt |
| Praktiske opgaver | deadlines, reminders, today-overblik, persistent memory |

## 3. Agentic AI

Agentic adfærd vises på to niveauer:

1. Proaktivt: scheduler igangsætter digest/nyhedsflow uden nyt brugerprompt.
2. Målstyret: `/assistant` kan vælge mellem read-only tools til dokumenter, deadlines, memories og nyheder, kombinere resultater og formulere et svar.

Sikkerhedsgrænse: agenten må ikke ændre data. Skriveoperationer kræver en eksplicit, struktureret slash command og permission check.

## 4. Praktiske regler

| Regel | Designkontrol |
|---|---|
| Ingen persondata | Ingen brugerprofiler/samtalehistorik/user IDs i DB; advarsler, retention og sletning |
| Ingen personlige konti/rigtige adgangskoder | Discord bot application til formålet; bot-token i `.env`; ingen brugerlogin gemmes |
| Undersøg leverandørvilkår | Discord og feedkilder dokumenteres; Ollama/AI er lokal; gruppen bekræfter vilkår før aflevering |
| Tag kopi før ændringer | Daglig/on-demand SQLite online backup + 7 kopier + restore-guide |

## 5. Slide 1 – “Hvordan virker assistenten?”

Gruppen kan med egne ord dække:

- Discord som fælles brugerflade
- Python-bot som styring
- dokument-RAG og de to lokale modeller
- SQLite-memory/deadlines
- scheduler/nyheder
- hvad der virker i prototype vs. planlagt

Brug `PROJECT_SPEC.md` og `ARCHITECTURE.md` til forståelse. Kopiér ikke automatisk teksten til afleveringen.

## 6. Slide 2 – dataflowdiagram

Diagrammet skal vise data, ikke blot teknologier:

- spørgsmål → Discord → bot → lokal model → svar
- dokument → lokal parsing/embeddings → SQLite
- memory/deadline → validering → SQLite → Discord
- RSS-data → bot → lokal klassifikation → SQLite/Discord
- hvilke data gemmes og retention

Brug `DATA_AND_PRIVACY.md` som facitliste, men tegn og navngiv selv.

## 7. Slide 3 – teknisk arkitekturdiagram

Diagrammet skal navngive teknologien og hvem der driver den:

- Discord / Discord Inc. / cloud
- SecMate backend / Python 3.12 / gruppens host
- discord.py / Discord Gateway og application commands
- Ollama API / localhost
- qwen3:4b / lokal chatmodel
- embeddinggemma / lokal retrievalmodel
- SQLite / lokal persistent database
- pypdf/feedparser / lokale biblioteker
- eksterne officielle feedudbydere

Brug `ARCHITECTURE.md` som facitliste, men lav diagrammet selv.

## 8. Begrænsninger som bør nævnes

- Host-computer skal være tændt.
- Discord og internet er stadig eksterne afhængigheder.
- Lokal model er langsommere/mindre stærk end store cloudmodeller.
- pypdf laver ikke OCR.
- AI-resuméer kan være forkerte; original kilde og citationscheck er vigtigt.
- MVP er til skolebrug, ikke produktion eller persondata.

