# Beslutninger og kontrollerede kilder

Kontrolleret: 15. september 2026. Codex skal kontrollere versionsfølsomme oplysninger igen ved implementering, især package releases og feed-URL'er.

## ADR-001 – Discord er eneste brugerflade

**Beslutning:** Slash commands og automatiske kanalopslag.

**Hvorfor:** Gruppen får én fælles opsætning uden at bygge login, hjemmeside eller app. Guild commands opdaterer straks under udvikling. Slash commands undgår behovet for at læse alt message content.

**Konsekvens:** Discord er stadig en ekstern tjeneste og ser de Discord-data, der sendes.

Kilder:

- [Discord Application Commands](https://docs.discord.com/developers/interactions/application-commands)
- [Discord Gateway intents](https://docs.discord.com/developers/events/gateway)
- [discord.py documentation](https://discordpy.readthedocs.io/)

## ADR-002 – Ollama og ingen cloud-AI

**Beslutning:** Ollama API på `http://127.0.0.1:11434`.

**Hvorfor:** Ingen betaling pr. kald, lokal dokumentbehandling og et stærkt sikkerhedsargument. Ollama dokumenterer lokalt base-URL og officiel Python-klient.

**Konsekvens:** Hostens hardware bestemmer hastighed, og hosten skal være tændt.

Kilder:

- [Ollama API introduction](https://docs.ollama.com/api/introduction)
- [Ollama Python library](https://github.com/ollama/ollama-python)

## ADR-003 – `qwen3:4b` som standardmodel

**Beslutning:** `qwen3:4b`, med `qwen3:1.7b` som lav-hardware fallback og `qwen3:8b` som frivillig opgradering.

**Hvorfor:** 4B-varianten er konkret tilgængelig i Ollama, cirka 2,5 GB, Apache 2.0, har tool support og understøtter 100+ sprog/dialekter.

**Konsekvens:** Modellen er mindre end store cloudmodeller. Tool output og faktuelle svar skal valideres/groundes.

Kilde:

- [Ollama model library: qwen3:4b](https://ollama.com/library/qwen3:4b)

## ADR-004 – `embeddinggemma` til RAG

**Beslutning:** Brug `embeddinggemma` til både dokument- og query-embeddings.

**Hvorfor:** Ollama anbefaler modellen til embeddings/RAG; den er 300M, cirka 622 MB, multilingual og on-device. Ollamas `/api/embed` kan batch-embedde og returnerer L2-normaliserede vectors.

**Konsekvens:** Modellen kræver Ollama 0.11.10+ og har 2K context, så chunks skal være korte. Skift af embeddingmodel kræver reindex.

Kilder:

- [Ollama embeddings capability](https://docs.ollama.com/capabilities/embeddings)
- [Ollama embed endpoint](https://docs.ollama.com/api/embed)
- [Ollama model library: embeddinggemma](https://ollama.com/library/embeddinggemma)

## ADR-005 – SQLite som eneste database

**Beslutning:** SQLite med migrations, WAL og online backup.

**Hvorfor:** Én host og få brugere kræver ikke ekstern database. SQLite giver persistence og let backup uden konto/service.

**Konsekvens:** Én databasefil og én primær writer passer til projektet, men multi-host skal ikke forsøges.

Kilder:

- [Python sqlite3 documentation](https://docs.python.org/3/library/sqlite3.html)
- [aiosqlite](https://pypi.org/project/aiosqlite/)

## ADR-006 – egen let RAG, ingen vector-service

**Beslutning:** Tekst/chunks/float32 embeddings gemmes i SQLite og rangeres i Python.

**Hvorfor:** Studiesamlingen er lille. Det holder systemet gratis, lokalt og forklarligt og undgår Pinecone/Chroma/cloud.

**Konsekvens:** Ikke optimeret til tusindvis/millioner af chunks. Retrieval-interface isoleres, så det kan udskiftes senere.

## ADR-007 – strukturerede commands til writes

**Beslutning:** LLM-agenten har kun read-only tools. Memory/deadline writes sker via slash commands.

**Hvorfor:** Datoer, sletninger og dataændringer må ikke baseres på en lille models frie fortolkning.

**Konsekvens:** Brugeren skriver fx `due_date=YYYY-MM-DD`, men systemet er mere sikkert og testbart.

Kilde:

- [Ollama tool calling](https://docs.ollama.com/capabilities/tool-calling)

## ADR-008 – `discord.ext.tasks` frem for ekstern scheduler

**Beslutning:** Periodisk minute-loop og SQLite idempotency.

**Hvorfor:** Færre dependencies/services. Discord.py har task helpers, mens SQLite gør genstart sikker.

**Konsekvens:** Botprocessen skal køre for at udføre jobs; dette er acceptabelt for prototypen.

Kilde:

- [discord.ext.tasks](https://discordpy.readthedocs.io/en/stable/ext/tasks/index.html)

## ADR-009 – direkte host-installation før Docker

**Beslutning:** Python venv + native Ollama i MVP.

**Hvorfor:** Ollama/GPU/Metal og Docker host networking varierer mellem macOS, Windows og Linux. Native setup er lettest at fejlfinde til demo.

**Konsekvens:** Miljøet er mindre containeriseret. Pinned dependencies, doctor-script og dokumentation giver reproducerbarhed.

## ADR-010 – RSS-resumé frem for webcrawl

**Beslutning:** Læs kun allowlistede RSS/Atom-data; crawl ikke artikelsider i MVP.

**Hvorfor:** Lavere kompleksitet, mindre SSRF/terms/HTML attack surface og ingen søge-API.

**Konsekvens:** Resuméet er begrænset til feedets indhold; originalt link er nødvendigt. Den foreslåede CISA feed-URL skal live-verificeres, fordi udbydere kan flytte/blokere feeds.

## Dependency-kontrol

Verificerede PyPI releases pr. kontroltidspunkt:

| Package | Version |
|---|---:|
| discord.py | 2.7.1 |
| ollama (Python client) | 0.6.2 |
| aiosqlite | 0.22.1 |
| feedparser | 6.0.14 |
| pypdf | 6.18.1 |
| python-dotenv | 1.2.3 |

Kilder: de respektive officielle [PyPI-projektsider](https://pypi.org/). Codex skal resolve kompatible versioner, fryse dem og køre `pip-audit`; denne tabel er ikke en erstatning for lockfil/tests.

## Vilkår gruppen skal kontrollere

- [Discord Privacy Policy](https://discord.com/privacy)
- [Discord Developer Terms of Service](https://support-dev.discord.com/hc/en-us/articles/8562894815383-Discord-Developer-Terms-of-Service)
- licens/vilkår for den konkrete undervisnings-PDF
- vilkår/robots/feed-policy for de valgte RSS-kilder
- modellicenser for de præcise Ollama-tags, hvis de ændres

Notér dato og konklusion med egne ord i gruppens arbejdsnoter før fremlæggelsen.

