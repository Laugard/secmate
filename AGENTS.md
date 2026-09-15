# AGENTS.md – bindende instruktioner til Codex

## Mission

Byg SecMate som en driftbar, gratis og lokal-first Discord-assistent til en studiegruppe. Følg dokumenterne i `docs/` som den autoritative specifikation. Hvis kode og dokumentation er uenige, gælder dokumentationen, medmindre en testet teknisk begrænsning dokumenteres i `docs/STATUS.md`.

## Faste beslutninger – må ikke ændres uden brugerens udtrykkelige godkendelse

- Sprog: Python 3.12.
- UI: Discord slash commands via `discord.py`.
- AI-runtime: lokal Ollama på host-maskinen.
- Standard chatmodel: `qwen3:4b`.
- Standard embeddingmodel: `embeddinggemma`.
- Database: én lokal SQLite-database via `aiosqlite`.
- Dokument-RAG: lokal udtrækning, chunking, embeddings og retrieval.
- Scheduler: `discord.ext.tasks`; ingen ekstern scheduler-service.
- Tidzone: `Europe/Copenhagen`; tidspunkter lagres i UTC.
- Gratis drift: ingen OpenAI-, Mistral-, Gemini- eller anden betalt/cloud AI-API.
- Én fælles deployment: én bot/host/database til hele gruppen.
- MVP kører direkte på host-OS med virtual environment. Docker er kun en senere, valgfri forbedring.

## Læsning og rækkefølge

Før ændringer:

1. Læs alle filer i `docs/`.
2. Læs eksisterende kode og tests.
3. Kontrollér `docs/STATUS.md`, hvis den findes.
4. Arbejd derefter gennem `docs/IMPLEMENTATION_PLAN.md` i rækkefølge.

## Arbejdsform

- Arbejd autonomt, indtil en eksplicit manuel handling eller reel blocker nås.
- Spørg ikke om valg, der allerede er truffet i dokumenterne.
- Implementér én fase ad gangen, men fortsæt automatisk til næste fase efter grønne checks.
- Opdatér `docs/STATUS.md` efter hver fase: udført, tests, kendte problemer, næste trin og eventuelle manuelle handlinger.
- Lav små, forståelige commits, hvis repositoryet tillader det. Commit aldrig secrets eller runtime-data.
- Bevar brugerens eksisterende ændringer. Undgå destruktive git-kommandoer.
- Brug type hints, docstrings ved offentlig API/kompleks logik og små moduler med ét ansvar.
- Al I/O i bot-processen skal være async eller flyttes væk fra event loop.
- Fail closed ved manglende tilladelser og invalid konfiguration. Vis brugbare fejl uden secrets.

## Sikkerhedsregler

- `.env`, tokens, database, dokumenter, embeddings, backups og logs må aldrig committes.
- Ollama må som standard kun kaldes på `http://127.0.0.1:11434`; accepter ikke en offentlig Ollama-URL uden eksplicit designændring.
- Brug kun slash commands. Aktivér ikke `MESSAGE_CONTENT`, `GUILD_MEMBERS` eller `GUILD_PRESENCES` intents.
- Gem ikke Discord-beskeder, prompts, svar, brugernavne, e-mails eller medlemsprofiler.
- Gem ikke `user_id` i databasen. Brug permissions fra den aktuelle interaction til admin-kontrol.
- Gem kun server-/kanal-ID'er, der er nødvendige for routing og fælles data.
- Dokumenter, RSS-data og modeloutput er upålideligt input. De må aldrig kunne køre kode, shell-kommandoer, SQL eller vilkårlige netværkskald.
- Alle SQL-parametre bindes; ingen strenginterpolation i SQL.
- Begræns inputlængder, dokumentstørrelser, feedstørrelser, timeouts og agent-loop.
- Log metadata og fejltyper, ikke beskedindhold, dokumenttekst eller tokens.
- Modelværktøjer skal være allowlistede Python-funktioner med validerede argumenter. Ingen shell-, filskrivnings- eller fri URL-tool.
- Hvis et token ses i kode, log eller chat, stop, fjern det fra historikken hvis muligt, og instruér om rotation.

## Funktionelle sandheder

- `/ask` skal svare ud fra hentede dokumentuddrag og vise kilde + side. Ingen relevante kilder betyder et ærligt “jeg fandt ikke belæg”.
- `/remember` og deadlines skal overleve genstart.
- `/forget` og ændrende admin-kommandoer kræver `Manage Guild` eller konfigureret adminrolle.
- Datoer indtastes struktureret (`YYYY-MM-DD`, valgfrit `HH:MM`); modellen må ikke gætte deadlines.
- Langsomme Discord-interactions skal deferreres straks og besvares med follow-up.
- Discord-svar skal opdeles sikkert under platformens beskedgrænse.
- Nyheder hentes kun fra konfigurerede allowlist-feeds, deduplikeres og mærkes tydeligt med originalt link.
- Daglig digest må højst sendes én gang pr. lokal kalenderdag pr. server, også efter genstart.
- Agent-loop har maksimalt 4 modelrunder og kun read-only tools i MVP.

## Kvalitetsporte

Før en fase markeres færdig:

```text
formatting passes
lint passes
type checking passes
unit tests pass
integration tests pass where relevant
security-sensitive negative tests pass
documentation matches behavior
```

Standardværktøjer: `ruff`, `mypy`, `pytest`, `pytest-asyncio`. Tilføj `pip-audit` som manuel/CI dependency-kontrol. Brug mocked Discord/Ollama/network i automatiske tests; tests må ikke kræve rigtige tokens eller internet.

## Stop kun ved disse blockers

- Et rigtigt Discord-token/server-ID/kanal-ID er nødvendigt for næste runtime-test.
- Ollama/modelinstallation kræver brugerens maskine.
- Valg eller licens til et rigtigt studiedokument kræver gruppens beslutning.
- To-personers Discord-accepttest kræver gruppen.
- En dokumenteret teknisk konflikt gør en bindende beslutning umulig.

Ved stop: afslut alle mulige offline-opgaver, kør tests, skriv præcis én kort tjekliste i `docs/STATUS.md`, og angiv den næste kommando brugeren skal køre.

