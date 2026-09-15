# Implementeringsplan – udføres af Codex i rækkefølge

## Statusmarkering

Codex skal oprette `docs/STATUS.md` med denne tabel og løbende opdatere den:

| Fase | Status | Tests | Blocker/næste trin |
|---|---|---|---|
| 0 | pending | | |
| 1 | pending | | |
| 2 | pending | | |
| 3 | pending | | |
| 4 | pending | | |
| 5 | pending | | |
| 6 | pending | | |
| 7 | pending | | |
| 8 | pending | | |
| 9 | pending | | |

En fase må kun blive `done`, når dens exit criteria er opfyldt. `blocked_manual` er tilladt efter alle mulige offline-tests er udført.

## Fase 0 – repository og guardrails

### Tasks

- Læs alle docs og registrér eventuelle reelle konflikter.
- Opret `pyproject.toml`, requirements, src-layout og test-layout.
- Brug Python 3.12.
- Tilføj runtime-dependencies: discord.py, ollama, aiosqlite, pypdf, feedparser, python-dotenv og aiohttp hvis brugt direkte.
- Tilføj dev-dependencies: pytest, pytest-asyncio, ruff, mypy, pip-audit.
- Pin/frys kompatible versioner efter installation; dokumentér versionsdato.
- Konfigurér ruff, mypy og pytest.
- Opret `README.md` med kort status og link til manual setup.
- Udvid `.gitignore` hvis nødvendigt.
- Opret CI til lint/type/tests uden secrets/network, hvis GitHub Actions er i scope.
- Opret `docs/STATUS.md`.

### Exit criteria

- Minimal package importerer.
- `pytest`, `ruff check`, `ruff format --check` og `mypy` kører grønt på skeleton.
- `git status` viser ingen runtime-data eller secrets.

## Fase 1 – konfiguration, logging og doctor

### Tasks

- Implementér typed config fra environment med fail-fast validering.
- Kritisk: token, test guild ID, databasepath, dokumentpath, loopback Ollama host.
- Valgfri kanal-konfiguration skal deaktivere feature med warning, ikke crashe.
- Afvis non-loopback Ollama host.
- Implementér sikker logging med rotation og redaction.
- Implementér `python scripts/doctor.py` eller `python -m secmate.doctor`.
- Doctor checker Python, mapper, write permissions, env-nøgler (kun present/missing), Ollama API og modelnavne.
- Doctor må ikke kræve Discord-login for offline check.

### Tests

- valid/invalid env
- non-loopback Ollama afvises
- secret redaction
- manglende valgfri channel giver warning
- mapper oprettes sikkert

### Exit criteria

- Doctor giver konkrete næste kommandoer uden at afsløre værdier.
- Alle offline quality checks grønne.

## Fase 2 – database og repositories

### Tasks

- Implementér connection factory og migrations fra `DATABASE_SCHEMA.md`.
- Implementér repositories for memories, deadlines, documents/chunks, news og job-runs.
- Brug parameterbinding og transaction boundaries.
- Implementér cleanup queries og SQLite online backup med integrity check.
- Injicér clock, så retention kan testes.

### Tests

- migrations/idempotens/rollback
- CRUD + guild isolation
- retention boundary dates
- unique daily job claim
- news dedupe
- document cascade delete
- backup + integrity check
- SQL injection payload behandles som data

### Exit criteria

- Integrationstest mod temporær SQLite-fil er grøn.
- Database kan genåbnes og data persisterer.

## Fase 3 – lokal Ollama-service

### Tasks

- Brug Ollama Python `AsyncClient` mod config host.
- Implementér health/list model check, chat, structured output og batch embed.
- Timeout, semaphore=1 og domænefejltyper.
- Ingen automatisk download af model i botten; health viser `ollama pull ...`.
- En request cancellation må ikke efterlade semaphore låst.
- Modeloutput/logs må ikke gemme prompts.

### Tests

- fake client success/error/timeout
- manglende modeller
- concurrency semaphore
- invalid structured JSON + én retry + fallback
- embed dimension mismatch

### Exit criteria

- Offline tests grønne.
- Valgfri live smoke test kan køres, hvis Ollama findes; ellers markeres kun den test `blocked_manual`.

## Fase 4 – dokumentingestion og RAG

### Tasks

- Implementér sikker filopdagelse under dokumentroden.
- PDF/MD/TXT parsing og OCR-detektionsfejl.
- Chunking med page metadata, overlap og deterministisk output.
- Batch embeddings og atomisk index replacement.
- Content hash + embedmodel gør reindex idempotent.
- Retrieval rangerer med dot product/cosine og score threshold.
- RAG-prompt beskytter mod prompt injection og kræver citations.
- Citations sammensættes/valideres fra metadata; modellen må ikke opfinde filnavne.
- CLI ingestion og admin `/reindex` service-interface.

### Tests

- sample PDF med kendt tekst/sidetal
- MD/TXT
- scanned/empty PDF
- for stor fil/for mange sider
- traversal og symlink escape
- idempotent reindex
- failed embed bevarer gammelt indeks
- relevant retrieval og no-evidence fallback
- dokument med “ignore previous instructions” ændrer ikke systemadfærd

### Exit criteria

- Et fixture-spørgsmål giver svar med korrekt `[fil, side]` via mocked LLM.
- Ingestionrapport er forståelig.

## Fase 5 – Discord-bot og MVP commands

### Tasks

- Implementér bot med minimale intents og app command tree.
- Sync commands til `DISCORD_TEST_GUILD_ID` under udvikling for øjeblikkelig opdatering.
- Implementér `/health`, `/ask`, `/remember`, `/memories`, `/forget`, deadline-command group, `/today` og `/reindex`.
- Defer alle potentielt langsomme interactions.
- Split lange beskeder og neutralisér mentions.
- Permission check på ændrende/admin commands.
- Cooldowns i hukommelsen; user ID må ikke persisteres.
- Central error handler på dansk.

### Tests

- command service tests med fake interactions
- permission denied/allowed
- inputlimit og invalid dato
- Discord 2000-tegn splitting
- `AllowedMentions.none()`
- Ollama nede men deterministic commands virker
- source citations i `/ask`

### Exit criteria

- Alle offline tests grønne.
- Live Discord-login og command sync må markeres `blocked_manual` indtil token/ID'er sættes.

## Fase 6 – scheduler, digest og backup

### Tasks

- Implementér minute-loop med lifecycle start/stop uden dublerede loops.
- Atomisk daily claim per guild/local date.
- Digest med deadlines + kildebaseret quiz/fallback.
- Daglig cleanup og backup med 7-copy retention.
- Ved Ollama-fejl sendes deterministic digestdel eller ingen besked efter dokumenteret regel; marker AI-del utilgængelig.
- Retry policy må ikke skabe dubletter.

### Tests

- før/efter planlagt tidspunkt
- DST-start/DST-slut i Europe/Copenhagen
- restart samme dag
- to samtidige claims
- send-fejl og retry
- missing channel
- cleanup/backup retention

### Exit criteria

- Simuleret clock viser præcis ét opslag pr. dag.
- Backup integritet verificeres.

## Fase 7 – sikkerhedsnyheder

### Tasks

- Hent kun allowlistede HTTPS-feeds fra lokal config.
- Download med timeout, byte-limit, redirect-policy og User-Agent.
- Parse RSS/Atom; sanitisér HTML til plain text.
- Canonicalize URL og dedupliker.
- Lokal model klassificerer i fast enum og skriver kort dansk structured output.
- Gem før post; markér posted efter succes.
- Map kategori til kanal-ID; fallback `andet`.
- Implementér `/news latest` og admin `/news refresh`.
- Scheduled refresh genbruger samme service.

### Tests

- RSS og Atom fixtures
- malformed feed/HTML
- timeout/for stort svar/redirect til ikke-allowlistet host
- prompt injection i feed summary
- invalid category/JSON fallback
- dedupe og restart
- missing category channel

### Exit criteria

- Fixture-feed fører til én korrekt kategoriseret post og ingen dublet på anden kørsel.
- Live feed-smoke test kan markeres `blocked_manual/network` uden at blokere offline kvalitet.

## Fase 8 – agentisk `/assistant`

### Tasks

- Implementér Ollama tool calling med fire read-only tools fra `PROJECT_SPEC.md`.
- Valider args, cap resultater/størrelse og maks. 4 agentrunder.
- Brug den samme RAG-/repository-logik som andre commands.
- Ingen writes, shell, arbitrary URL eller dynamisk Python-dispatch.
- Returnér kildehenvisninger og en tool-aktivitetssummering uden chain-of-thought.

### Tests

- nul tool calls
- ét og flere tilladte tools
- ukendt tool
- invalid args
- loop uden stop rammer cap
- tool exception giver sikkert delsvar
- prompt injection kan ikke få write/shell tool

### Exit criteria

- Eksempelrequest kombinerer deadline og dokumentkilde i ét svar.
- Negative sikkerhedstests grønne.

## Fase 9 – samlet verifikation og handoff

### Tasks

- Kør alle quality gates og dependency audit.
- Kør `scripts/smoke_test.py` med fakes.
- Opdatér README med macOS/Windows/Linux commands, startup, stop, backup og troubleshooting.
- Gennemgå `ACCEPTANCE_TESTS.md`; markér automatiske tests med evidens.
- Opret `docs/LIVE_TEST_RESULTS.md` skabelon til gruppens manuelle resultater.
- Kontrollér git for secrets/runtime data.
- Tag release-tag `v0.1.0` først efter live Must-tests.

### Exit criteria

- Alle automatiske Must-tests grønne.
- Manualen har kun de nødvendige brugerhandlinger.
- Codex stopper med én præcis liste over resterende live-steps.

## Prioritering ved tidspres

1. Fase 0–5: kravets sikre minimum.
2. Fase 6: proaktivitet/motivation/praktisk.
3. Fase 7: oprindelig nyhedsidé.
4. Fase 8: stærkere agentic-demonstration.
5. Fase 9: polish og evidens.

Codex må ikke ofre sikkerhed, persistence eller kildehenvisninger for at nå en senere fase.

