# Codex-prompts

Brug kun disse prompts, hvis Codex ikke allerede fortsætter autonomt. Start altid med master-prompten i `00_START_HERE.md`.

## Fortsæt fra status

```text
Read AGENTS.md, docs/STATUS.md, and the authoritative specification files. Inspect the current code and git diff. Resume from the first incomplete phase in docs/IMPLEMENTATION_PLAN.md. Implement, test, fix, document, and continue autonomously until a listed manual action or genuine blocker is reached. Do not change the fixed architecture or introduce cloud/paid AI.
```

## Få Codex til at kontrollere hele projektet

```text
Perform the Phase 9 verification now. Read docs/ACCEPTANCE_TESTS.md and map every automated MUST test A-01 through A-28 to an actual test and result. Run formatting, lint, type checking, unit/integration tests, dependency audit, secret/runtime-file checks, and the fake smoke test. Fix all failures within scope. Update docs/STATUS.md and create/update docs/LIVE_TEST_RESULTS.md with only the remaining manual live steps. Do not claim live tests passed unless a human actually performed them.
```

## Når I har sat `.env` og Ollama op

```text
The local manual setup is now available on this host. Do not print or inspect secret values. Run the doctor and safe live smoke checks for Ollama models, database, and Discord command sync. Fix code/configuration-shape issues, but do not rotate or expose credentials. Then tell me only which tests still require a human in Discord.
```

## Hvis Discord commands ikke vises

```text
Diagnose why SecMate application commands are not visible in the configured test guild. Preserve the slash-command-only and no-privileged-intents design. Check startup logs, config validation, guild-scoped tree sync, application installation scopes, and error handling. Do not request that the bot receive Administrator or Message Content intent. Add a regression test where possible and update docs/STATUS.md.
```

## Hvis `/ask` svarer forkert eller uden kilde

```text
Diagnose the SecMate RAG failure using the known test document and expected page. Trace ingestion, page numbering, chunking, embedding model consistency, vector serialization, similarity ranking, threshold, prompt construction, and citation validation. Never solve it by allowing uncited model knowledge. Add a regression fixture/test, preserve atomic reindexing, and update docs/STATUS.md.
```

## Hvis botten poster digest to gange

```text
Treat the duplicate daily digest as a correctness bug. Reproduce it with an injected clock and simulated restart/concurrent scheduler ticks. Fix the SQLite transactional claim and retry semantics so (job_name, guild_id, local_date) yields at most one successful post. Add regression tests for restart and concurrency. Do not merely add an in-memory flag.
```

## Hvis nyhedsfeed fejler

```text
Diagnose the configured allowlisted news feed without weakening SSRF, HTTPS, timeout, byte-limit, redirect, or deduplication controls. Verify the endpoint manually only if network access is available. Keep feed URLs configuration-only, add fixture coverage for the failure mode, and provide an exact safe configuration change if the provider moved the official feed.
```

## Bed Codex gøre klar til demo

```text
Prepare SecMate for a classroom demo using docs/DEMO_RUNBOOK.md. Run all safe automated checks, create a fresh verified SQLite backup, verify no secrets/runtime data are tracked, and produce a short operator checklist in docs/STATUS.md. Do not generate the assignment's three slides or claim human live tests were performed.
```

## Bed Codex lave én samlet gennemgang af sikkerheden

```text
Review the implemented system against docs/SECURITY.md and docs/DATA_AND_PRIVACY.md. Report concrete evidence from code/tests for every control. Fix implementation gaps within the agreed scope. Pay special attention to privileged Discord intents, loopback-only Ollama, secret logging, prompt injection, citation integrity, SQL parameterization, path traversal/symlinks, SSRF, timeouts, resource limits, permissions, retention, and backup integrity. Update tests and docs/STATUS.md.
```

## Det I ikke skal bede Codex om

- “Brug bare OpenAI/ChatGPT API” – det bryder gratis/lokal-kravet.
- “Gør Ollama tilgængelig på nettet” – gruppen bruger Discord; porten skal forblive lokal.
- “Læs alle beskeder i kanalen” – slash commands er nok og mere privat.
- “Lad modellen selv redigere databasen” – ændringer skal være strukturerede commands.
- “Push `.env` så gruppen kan bruge den” – del secrets via sikker kanal/password manager.
- “Lav vores tre slides i egne ord” – opgaven kræver gruppens egne formuleringer.

