# SecMate

SecMate er en lokal-first Discord-assistent til en IT-sikkerhedsstudiegruppe. Discord er brugerfladen; Python-botten, SQLite, dokumentindekset og begge Ollama-modeller kører på én fælles host. Der bruges ingen betalt eller ekstern AI-API.

## Funktioner

- `/ask` søger lokalt i PDF/Markdown/TXT og viser kilde + side.
- `/remember`, `/memories` og admin-only `/forget` gemmer fælles, ufølsomme noter.
- `/deadlines add|list|complete|delete` giver deterministiske deadlines i dansk tid.
- `/today` og en daglig digest giver deadlines og et kildebaseret quizspørgsmål.
- `/news latest|refresh` henter kun konfigurerede HTTPS RSS/Atom-feeds, deduplikerer og bruger lokal AI til dansk resumé.
- `/assistant` kan kombinere fire allowlistede read-only tools i højst fire modelrunder.
- `/health` viser database, Ollama, modeller, dokumentindeks og kanalkonfiguration.
- Daglig cleanup og verificeret SQLite online-backup med syv kopier.

## Krav

- Python 3.12
- Ollama 0.11.10 eller nyere på samme computer
- `qwen3:4b` og `embeddinggemma`
- En Discord application/bot uden privileged intents og uden Administrator

Den komplette klik-for-klik-vejledning står i [docs/MANUAL_SETUP.md](docs/MANUAL_SETUP.md).

## Installation

### macOS/Linux

```bash
python3.12 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
cp .env.example .env
```

### Windows PowerShell

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
Copy-Item .env.example .env
```

Udfyld `.env` lokalt; commit eller del aldrig tokenet. Behold `OLLAMA_HOST=http://127.0.0.1:11434`.

```bash
ollama pull qwen3:4b
ollama pull embeddinggemma
python scripts/doctor.py
python scripts/ingest_documents.py
python -m secmate
```

Stop sikkert med `Ctrl+C`. Grundlæggende databasekommandoer virker fortsat, hvis Ollama er nede.

## Udvikling og tests

```bash
python -m pip install -r requirements-dev.txt
python -m ruff format --check .
python -m ruff check .
python -m mypy src/secmate
python -m pytest -q
python scripts/smoke_test.py
python -m pip_audit -r requirements.txt
```

Automatiske tests kræver hverken internet, Discord-token eller Ollama.

## Dokumenter og backup

Læg kun tilladte, ikke-fortrolige og maskinlæsbare `.pdf`, `.md` eller `.txt` i `data/documents/`. OCR er ikke understøttet. Kør `python scripts/ingest_documents.py` eller admin `/reindex`.

Opret en verificeret online-backup med:

```bash
python scripts/backup_db.py
```

Restore: stop botten, tag en kopi af den nuværende DB, kontrollér backup med `PRAGMA integrity_check`, erstat DB-filen, start igen og kør doctor. Slettede data kan findes i backups, indtil de syv roterede kopier er væk.

## Tokenrotation

Discord Developer Portal → Bot → Reset Token. Opdatér kun den lokale `.env`, genstart botten og kontrollér med doctor. Hvis et token nogensinde vises i chat, log, screenshot eller git, skal det straks roteres.

## Fejlsøgning

- Manglende commands: kontrollér test-guild-ID, installations-scopes og genstart.
- Ollama utilgængelig/model mangler: kør `ollama list` og de pull-kommandoer doctor viser.
- `/ask` uden belæg: kontrollér dokumenttype, kør reindex og brug et spørgsmål med kendt svar.
- Forkert PDF-side: menneskelig side er parserindeks + 1; verificér mod originalen.
- Feedfejl: opdatér kun til en officiel HTTPS-feed-URL i `.env`; svæk ikke allowlisten.

Se [docs/STATUS.md](docs/STATUS.md) for teststatus og resterende manuelle trin.

