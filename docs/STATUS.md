# Implementeringsstatus

Senest opdateret: 15. september 2026.

| Fase | Status | Tests | Blocker/næste trin |
|---|---|---|---|
| 0 | done | import, Ruff, format, mypy, pytest, CI | Ingen |
| 1 | done | config, loopback/cloud-afvisning, redaction, mapper | Live doctor kræver lokal `.env`/Ollama |
| 2 | done | migration, CRUD, guild-isolation, SQL-payload, retention, claim, WAL-backup | Ingen offline-blocker |
| 3 | done | fake success/error/timeout, structured fallback, dimensions, semaphore | Live Ollama-test kræver lokal installation |
| 4 | done | PDF/MD, side, chunking, idempotens, atomic failure, retrieval/no-evidence, symlink/size/OCR | Rigtigt studiedokument vælges manuelt |
| 5 | done | minimale intents, permissions, limits, defer-kontrakt, splitting/mentions, citations | Discord-login/sync kræver token og guild |
| 6 | done | atomic daily claim/restart, digest fallback, cleanup og backup/rotation | Live kanalopslag kræver Discord |
| 7 | done | RSS-fixture, HTML-sanitization, HTTPS, injection-resistens, JSON fallback, dedupe | Officielt feed og kanaler live-testes manuelt |
| 8 | done | allowlist, flere runder, ukendt tool og 4-runders cap | Live model-toolcalling kræver Ollama |
| 9 | blocked_manual | 44 tests, Ruff, format, strict mypy, smoke og audit grønne | L-01–L-06 og lokal doctor mangler |

## Seneste automatiske evidens

```text
Python 3.12.14
ruff format --check: pass
ruff check: pass
mypy src/secmate: pass (strict)
pytest: 44 passed
scripts/smoke_test.py: pass
pip-audit requirements.txt: No known vulnerabilities found
```

Dependency-pins blev kontrolleret 15. september 2026. Den oprindelige `aiohttp 3.12.15` gav 32 advisories i audit og blev derfor erstattet af den rettede `aiohttp 3.14.3`; hele testsuiten bestod efter opgraderingen.

## Automatiske MUST-tests A-01–A-28

Alle er dækket af automatiske tests eller direkte kontrakttests og er grønne. Centrale filer: `tests/test_config.py`, `test_database.py`, `test_ollama.py`, `test_rag_ingestion.py`, `test_news_agent.py`, `test_discord_contract.py` og `test_repository_guardrails.py`.

## Præcis resterende manuel tjekliste

1. Opret/invitér Discord-botten uden privileged intents eller Administrator; kopiér token, guild-ID og kanal-ID'er til lokal `.env`.
2. Installér/start Ollama lokalt og kør `ollama pull qwen3:4b` samt `ollama pull embeddinggemma`.
3. Installér Python 3.12-dependencies og kør `python scripts/doctor.py`; næste kommando er derefter `python scripts/ingest_documents.py`.
4. Vælg mindst én tilladt, maskinlæsbar og ikke-fortrolig PDF, I ikke selv har skrevet, og læg den i `data/documents/`.
5. Start `python -m secmate` og gennemfør L-01–L-06 med mindst to gruppemedlemmer; registrér kun anonymiseret evidens i `docs/LIVE_TEST_RESULTS.md`.
6. Kør `python scripts/backup_db.py` før demo. Tag først release-tag `v0.1.0`, når alle live MUST-tests er bestået.

