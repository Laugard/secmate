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
| 9 | blocked_manual | 51 tests, Ruff, format, strict mypy, smoke og audit grønne | L-01–L-06 og lokal doctor mangler |

## Kodegennemgang 15. september 2026

Rettet efter de første live-tests i Discord:

- `/health` viste embeddingmodellen rød: Ollama rapporterer `embeddinggemma:latest`, og sammenligningen ignorerer nu det implicitte `:latest`-tag.
- `/ask` skrev "Belæg mangler" og en kilde i samme svar: modellen svarer nu med et fast token (`INGEN_BELÆG`), som koden afgør no-evidence-grenen på, og viser i stedet "Nærmeste uddrag".
- `/news refresh` gav "feedfejl: 1": cisa.gov svarer 403 til en bar produkt-User-Agent. Feedklienten sender nu en konventionel feedlæser-header med kontakt-URL (verificeret live: 30 entries), og fejlteksten viser vært og HTTP-status.
- Nyheder blev klassificeret af modellen FØR dedupe, så hver refresh kostede én generering per allerede gemt entry. Dedupe sker nu først; `published_at_utc` udfyldes fra feedet.
- Strukturerede kald bruger Ollamas `format=json` og accepterer kodeindhegnet JSON; `think=False` slår qwen3's skjulte tænkepas fra, som ellers brugte timeout-budgettet.
- Daglig oprydning og backup kørte kun i minuttet 02:00 præcis; en slukket host kørte den derfor aldrig. Den følger nu samme "én gang per dato ved eller efter tidspunktet"-regel som digest. En fejl i scheduler-loopet stopper ikke længere loopet stille; den logges.
- Logfilteret redigerede formatstrengen før argumenterne blev sat ind, så `%s`-værdier gik tabt i loggen. Advarsler vises nu også i terminalen.
- Windows har ingen tidszonedatabase; `tzdata` er tilføjet til requirements (tre tests fejlede uden).
- Mindre: `/news latest` har kategori-valg i Discord, agentens tools har rigtige parameterskemaer, digest viser lokal tid og vælger et tilfældigt uddrag til quizzen, embeddings sendes i batches af 32, cosine-similarity bruger `math.sumprod`.

## Seneste automatiske evidens

```text
Python 3.12.13
ruff format --check: pass
ruff check: pass
mypy src/secmate: pass (strict)
pytest: 51 passed
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

