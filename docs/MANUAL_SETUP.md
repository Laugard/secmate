# Manuel opsætning – kun det gruppen selv skal gøre

Følg rækkefølgen. Indsæt aldrig et rigtigt token i chat, Codex-prompt, GitHub, screenshot eller denne fil.

## Del A – GitHub og Codex

1. Opret et tomt repository, fx `secmate`.
2. Læg hele starter-pakken i repositoryets rod.
3. Bekræft, at `AGENTS.md`, `.gitignore`, `.env.example` og `docs/` ligger i roden.
4. Commit dokumenterne.
5. Tilknyt repositoryet til et Codex-projekt.
6. Brug første prompt fra `00_START_HERE.md`.
7. Lad Codex implementere fase 0–4 uden rigtige secrets.

## Del B – opret projektets Discord-server

Brug en server oprettet til formålet. Forslag:

```text
📚 STUDIE
#spørg-secmate
#dagens-quiz
#deadlines

📰 SECURITY NEWS
#sårbarheder
#cyberangreb
#ai-security
#lovgivning
#andet

🔧 DRIFT
#secmate-status
```

Begræns adgang til gruppen. Brug ikke persondata i kanalnavne eller testbeskeder.

## Del C – opret Discord-applikation og bot

Discords portal ændrer indimellem UI-ordlyd, men målet er dette:

1. Gå til [Discord Developer Portal](https://discord.com/developers/applications).
2. Vælg **New Application** og kald den `SecMate`.
3. Åbn **Bot** og opret botten, hvis den ikke allerede findes.
4. Generér/reset bot-token.
5. Kopiér tokenet direkte til en lokal password manager eller senere `.env`. Del det ikke med gruppen i Discord.
6. Under **Privileged Gateway Intents** skal alle disse forblive slukket:
   - Presence Intent
   - Server Members Intent
   - Message Content Intent
7. Under installation/OAuth2 vælg server/guild-installation med scopes:
   - `bot`
   - `applications.commands`
8. Vælg kun de nødvendige bot permissions:
   - View Channels
   - Send Messages
   - Embed Links
   - eventuelt Read Message History, kun hvis live test viser et konkret behov
9. Vælg projektserveren og invitér botten.
10. Botten er offline, indtil Python-processen startes; det er normalt.

Giv aldrig botten Administrator.

## Del D – find Discord-ID'er

1. Discord → User Settings → Advanced → slå **Developer Mode** til.
2. Højreklik serverikonet → **Copy Server ID**.
3. Højreklik hver kanal → **Copy Channel ID**.
4. Hvis I bruger en særlig adminrolle: højreklik rollen → **Copy Role ID**.
5. Gem dem lokalt til `.env`; de er ikke secrets på samme niveau som tokenet, men bør stadig ikke spredes unødigt.

## Del E – installer Python

Brug Python 3.12.x.

Kontrollér:

```bash
python3.12 --version
```

På Windows kan kommandoen være:

```powershell
py -3.12 --version
```

Opret miljø efter Codex har lavet koden:

### macOS/Linux

```bash
python3.12 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

### Windows PowerShell

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

Hvis PowerShell afviser aktiveringsscript, brug Command Prompt eller en process-scope execution-policy efter skolens regler; ændr ikke hele maskinens sikkerhedspolitik ukritisk.

## Del F – installer Ollama og lokale modeller

1. Download Ollama fra [ollama.com/download](https://ollama.com/download).
2. Installér og start Ollama.
3. Kontrollér lokalt API:

```bash
ollama --version
ollama list
```

4. Download standardmodeller:

```bash
ollama pull qwen3:4b
ollama pull embeddinggemma
```

`qwen3:4b` fylder cirka 2,5 GB i Ollamas modelbibliotek. `embeddinggemma` fylder cirka 622 MB og kræver Ollama 0.11.10 eller nyere.

Hvis hosten reelt er for langsom:

- under ca. 8 GB tilgængelig RAM: prøv `qwen3:1.7b`
- 8–16 GB: behold `qwen3:4b`
- 16+ GB og god maskine: `qwen3:8b` kan prøves

Skift kun `OLLAMA_CHAT_MODEL` i `.env`. Behold `embeddinggemma`, medmindre hele dokumentindekset slettes og bygges igen med den nye embeddingmodel.

Ollama må forblive på `127.0.0.1:11434`. I behøver ikke åbne port 11434, fordi gruppemedlemmer bruger Discord, ikke Ollama direkte.

## Del G – lokal `.env`

1. Kopiér `.env.example` til `.env`.
2. Sæt token, server-ID og kanal-ID'er.
3. Behold:

```text
OLLAMA_HOST=http://127.0.0.1:11434
APP_TIMEZONE=Europe/Copenhagen
```

4. Kør:

```bash
python scripts/doctor.py
```

5. Løs kun de fejl, doctor viser.
6. Før commit: kontrollér at `.env` ikke er tracket:

```bash
git status --short
git check-ignore .env data/secmate.db
```

## Del H – vælg studiedokument

Krav til mindst én demonstrationskilde:

- I har ikke selv skrevet den.
- I må bruge den i projektet.
- Den indeholder ingen persondata eller fortroligt materiale.
- Den er maskinlæsbar, ikke kun scannede billeder.
- I ved på forhånd én side og ét spørgsmål, der kan verificere citationen.

Læg filen i:

```text
data/documents/
```

Indeksér med den CLI, Codex implementerer, fx:

```bash
python scripts/ingest_documents.py
```

eller start botten og kør admin `/reindex`.

Kontrollér resultatet med `/health` og et kendt `/ask`-spørgsmål.

## Del I – start botten

Aktivér venv og kør:

```bash
python -m secmate
```

Forventet startup-log:

```text
configuration valid
database migrated
ollama reachable
required models present
commands synced to test guild
SecMate ready
```

Den faktiske log må ikke vise token, prompts eller dokumenttekst.

## Del J – første live test

1. Host kører `/health`.
2. Admin kører `/reindex`.
3. Person A kører `/ask <kendt spørgsmål>`.
4. Person A kører `/remember Demoens deadline er 2026-...`.
5. Stop/start bot.
6. Person B kører `/memories` og `/deadlines list`.
7. Flyt midlertidigt digest-tidspunktet 2–3 minutter frem og test ét automatisk opslag.
8. Sæt tidspunktet tilbage efter testen.

Dokumentér i `docs/LIVE_TEST_RESULTS.md` uden persondata.

## Del K – backup og sikker stop

Før større ændringer og demo:

```bash
python scripts/backup_db.py
```

Stop botten med `Ctrl+C` og vent på shutdown-log. Sluk ikke processen midt i migration/reindex, hvis det kan undgås.

## Fejlsøgning

| Symptom | Sandsynlig årsag | Handling |
|---|---|---|
| Bot offline | Python-processen kører ikke/token forkert | Kør doctor; start `python -m secmate` |
| Slash commands mangler | Forkert guild ID eller sync | Kør doctor; genstart; brug test-guild sync |
| Ollama connection refused | Ollama ikke startet | Start Ollama; kontrollér `ollama list` |
| Model not found | Model ikke pulled | Kør de viste `ollama pull` commands |
| `/ask` finder intet | Ingen docs/reindex/threshold | Kontrollér `/health`, ingest report og kendt tekst |
| Forkert PDF-side | Parserens sideindeks/off-by-one | Brug menneskelig side = pypdf index + 1; test fixture |
| Digest dubleres | Job claim ikke atomisk/DB slettet | Stop demo; få Codex til at rette A-25/A-26 |
| Feed giver 403/404 | Endpoint ændret/blokerer klient | Skift kun til verificeret officiel RSS/Atom URL i `.env`; dokumentér |
| Bot langsom | Model/hardware | Defer, vent, brug `qwen3:1.7b` som dokumenteret fallback |

