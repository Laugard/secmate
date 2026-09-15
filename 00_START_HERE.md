# SecMate – start her

Denne mappe er en komplet krav- og arbejdsbeskrivelse til et nyt Codex-projekt. Den indeholder ikke den færdige programkode. Codex skal bygge koden ud fra materialet.

## Det system Codex skal bygge

SecMate er en fælles Discord-assistent til en studiegruppe. Én computer hoster:

- en Python-bot
- Ollama
- en lokal sprogmodel
- lokal dokument-søgning (RAG)
- en SQLite-database
- automatiske påmindelser og sikkerhedsnyheder

Gruppemedlemmerne bruger den samme bot i den samme Discord-server. Der er ingen betaling pr. AI-kald, og undervisningsdokumenter sendes ikke til en ekstern AI-leverandør. Discord-beskeder passerer stadig gennem Discord.

## Gør præcis dette

1. Opret et tomt GitHub-repository, fx `secmate`.
2. Pak denne mappe ud i roden af repositoryet.
3. Upload/commit filerne. Behold `AGENTS.md` i repositoryets rod.
4. Opret et nyt Codex-projekt med repositoryet.
5. Giv Codex prompten i afsnittet nedenfor.
6. Lad Codex arbejde gennem `docs/IMPLEMENTATION_PLAN.md` i rækkefølge.
7. Når Codex når den manuelle opsætning, følger I `docs/MANUAL_SETUP.md`.
8. Læg mindst én tilladt PDF, som I ikke selv har skrevet, i `data/documents/` og kør indekseringen.
9. Gennemfør alle testene i `docs/ACCEPTANCE_TESTS.md`.
10. Brug `docs/DEMO_RUNBOOK.md` til demonstrationen.

## Første prompt til Codex

```text
Build the complete SecMate project described in this repository.

First read AGENTS.md and every Markdown file in docs/. Treat them as the authoritative specification. Then inspect the repository and execute docs/IMPLEMENTATION_PLAN.md phase by phase in order.

Work autonomously until a listed manual user action or a genuine blocker is reached. Do not ask me to make ordinary technical choices that are already decided in the documents. Do not use any paid or cloud AI API. Ollama must remain local-only, SQLite must be the only application database, and Discord slash commands must be the user interface.

For each phase: implement it, add or update tests, run the relevant checks, fix failures, update docs/STATUS.md, and commit a clear checkpoint if git commits are available. Preserve security and privacy requirements. Never put secrets, the SQLite database, local documents, backups, or logs in git.

Begin now with Phase 0 and continue as far as possible.
```

## Hvad I selv stadig skal gøre

Codex kan skrive og teste næsten al kode, men kan ikke sikkert gøre følgende uden jer:

- oprette Discord-applikationen og hente bot-tokenet
- invitere botten til jeres Discord-server
- kopiere server- og kanal-ID'er
- installere/køre Ollama på host-computeren og downloade modellerne
- vælge og kontrollere rettighederne til de PDF'er, I lægger ind
- sætte de rigtige værdier i jeres lokale `.env`
- holde host-computeren tændt, når andre skal bruge botten
- udføre den endelige Discord-test med mindst to gruppemedlemmer
- formulere og tegne de tre afleveringsslides med jeres egne ord

## Vigtig grænse fra opgaven

Materialet her er teknisk projektdokumentation til udviklingen. Det er ikke en færdig aflevering af de tre slides. Opgaveteksten siger, at slides og diagrammer skal være jeres egne ord/arbejde, så brug systemet og dokumentationen til at forstå løsningen og tegn/formulér derefter selv.

## Dokumentoversigt

| Fil | Formål |
|---|---|
| `AGENTS.md` | Bindende arbejdsregler for Codex |
| `docs/PROJECT_SPEC.md` | Funktioner, scope og kvalitetskrav |
| `docs/ARCHITECTURE.md` | Komponenter, ansvar og tekniske flows |
| `docs/DATA_AND_PRIVACY.md` | Dataflow, lagring og slettefrister |
| `docs/SECURITY.md` | Trusselsmodel og sikkerhedskrav |
| `docs/DATABASE_SCHEMA.md` | SQLite-tabeller og regler |
| `docs/IMPLEMENTATION_PLAN.md` | Faser og konkrete tasks |
| `docs/ACCEPTANCE_TESTS.md` | Krav, testcases og Definition of Done |
| `docs/MANUAL_SETUP.md` | Det I selv skal klikke/installere/indtaste |
| `docs/CODEX_PROMPTS.md` | Prompts ved opstart, fortsættelse og fejlfinding |
| `docs/DEMO_RUNBOOK.md` | Stabil demo, rollback og nødplan |
| `docs/ASSIGNMENT_TRACEABILITY.md` | Hvor hvert skolekrav bliver opfyldt |
| `docs/DECISIONS_AND_SOURCES.md` | Teknologivalg og kontrollerede kilder |
| `.env.example` | Alle konfigurationsværdier uden hemmeligheder |

