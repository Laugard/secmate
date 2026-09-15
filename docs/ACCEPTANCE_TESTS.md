# Acceptancetests og Definition of Done

## 1. Testregler

- `MUST` skal bestås før MVP-demo.
- `SHOULD` skal bestås til komplet v0.1, men kan markeres med dokumenteret begrænsning ved tidspres.
- Automatiske tests må ikke bruge rigtigt Discord-token, internet eller kørende Ollama.
- Live tests udføres separat og dokumenteres i `docs/LIVE_TEST_RESULTS.md` med dato, tester, resultat og kort evidens uden secrets/persondata.

## 2. Automatiske MUST-tests

| ID | Test | Forventet resultat |
|---|---|---|
| A-01 | Start med manglende `DISCORD_TOKEN` | Fail fast med navn på manglende setting; ingen values |
| A-02 | `OLLAMA_HOST=http://0.0.0.0:11434` eller remote host | Konfiguration afvises |
| A-03 | Kør migrations to gange | Samme schema, ingen datatab |
| A-04 | Gem memory, luk DB, åbn igen | Memory findes stadig |
| A-05 | Guild A og B har data | Ingen cross-guild læk |
| A-06 | SQL payload i memorytitel | Gemmes/afvises som data; schema intakt |
| A-07 | Udløbet memory cleanup | Slettet ved grænsen; aktiv note bevares |
| A-08 | Backup af aktiv WAL-database | Backup integrity check = `ok` |
| A-09 | Kendt PDF fixture indekseres | Rigtigt antal sider/chunks og kildenavn |
| A-10 | Reindex samme hash/model | Ingen dubletchunks |
| A-11 | Embed-fejl midt i reindex | Gammelt fungerende indeks bevares |
| A-12 | Path traversal/symlink escape | Afvises |
| A-13 | PDF uden udtrækkelig tekst | Tydelig OCR/out-of-scope fejl |
| A-14 | Relevant query | Korrekt chunk i top-K |
| A-15 | Irrelevant query under threshold | No-evidence status |
| A-16 | Kilde indeholder prompt injection | Instruktionen udføres ikke; ingen tool/write |
| A-17 | Model opfinder citation | Outputcitation erstattes/afvises; kun retrieval metadata vises |
| A-18 | Input over max | Afvises før modelkald |
| A-19 | Slow command | Interaction defer kaldes før arbejde |
| A-20 | Output over Discord-grænse | Splittes uden at overskride; mentions deaktiveret |
| A-21 | Ikke-admin bruger `/forget`/add/delete/reindex | Permission denied, ingen ændring |
| A-22 | Invalid dato og DST-edge | Deterministisk fejl eller korrekt UTC-konvertering |
| A-23 | Ollama timeout | Sikker dansk fejl; semaphore frigives |
| A-24 | Ollama nede | `/memories`, `/deadlines list` og DB-health virker |
| A-25 | Digest loop to gange samme dag | Præcis én claim/post |
| A-26 | Bot restart samme dag | Ingen ekstra digest |
| A-27 | Logs med fake token/prompt | Token redacted; prompt/content ikke logget |
| A-28 | Git-ignore fixturecheck | `.env`, DB, docs, backups og logs ignoreres |

## 3. Automatiske SHOULD-tests

| ID | Test | Forventet resultat |
|---|---|---|
| A-29 | RSS + Atom fixtures | Begge parses til fælles model |
| A-30 | Samme news link to gange | Én DB-række/post |
| A-31 | For stort feed-svar | Afbrydes ved byte-limit |
| A-32 | Redirect til ikke-allowlistet host | Afvises |
| A-33 | Feed prompt injection | Kan ikke ændre kategori-enum/system/tools |
| A-34 | Ugyldigt model-JSON | Én retry, derefter sikkert fallback |
| A-35 | Manglende category channel | Data gemmes; post skippes med warning |
| A-36 | Agent ukendt tool | Afvist uden dynamisk execution |
| A-37 | Agent fortsætter uendeligt | Stop efter 4 runder |
| A-38 | Agent kombinerer deadline + docs | Begge toolresultater bruges og kilder vises |
| A-39 | Daily cleanup | Retention for news/job-runs/backups overholdes |

## 4. Live MUST-tests

### L-01 – fælles opsætning

**Forudsætning:** Bot kører på én host og er i projektserveren.

1. Gruppemedlem A kører `/health`.
2. Gruppemedlem B kører `/health` fra egen Discord-klient.
3. Begge ser samme bot og dokumentchunk-count.

**Bestået:** Mindst to personer bruger samme bot, ikke lokale kopier.

### L-02 – ekstern kilde og citation

1. Placér en tilladt PDF, I ikke selv har skrevet, i `data/documents/`.
2. Kør `/reindex` som admin.
3. Kør `/ask` med et spørgsmål, hvis svar findes på en kendt side.
4. Sammenlign svar og citation med PDF'en.

**Bestået:** Svar er fagligt dækket af kilden og viser korrekt fil + side. Ingen relevant kilde giver et ærligt no-evidence svar.

### L-03 – hukommelse mellem brug

1. Kør `/remember Afleveringsmødet er fredag kl. 10` (kun hvis oplysningen ikke er persondata).
2. Se den med `/memories`.
3. Stop botten normalt.
4. Start botten igen.
5. Kør `/memories` fra et andet gruppemedlem.

**Bestået:** Samme note findes efter genstart og for begge brugere.

### L-04 – deadline

1. Admin kører `/deadlines add` med kendt testdato.
2. Anden bruger kører `/deadlines list`.
3. Sammenlign dansk tid/dage.

**Bestået:** Samme deadline vises korrekt og persisterer.

### L-05 – proaktiv digest

1. Sæt midlertidigt digest-tid 2–3 minutter frem.
2. Start bot før tidspunktet.
3. Vent på opslag.
4. Genstart bot efter opslag samme dag.

**Bestået:** Præcis ét automatisk opslag i korrekt kanal; ingen dublet.

### L-06 – least privilege og lokal AI

1. Kontrollér Developer Portal: privileged intents er off; bot er ikke Administrator.
2. Afbryd Ollama og kør `/health` og `/deadlines list`.
3. Start Ollama igen og kør `/ask`.
4. Kontrollér at Ollama endpoint er loopback.

**Bestået:** Designet og degraderet drift matcher kravene.

## 5. Live SHOULD-tests

### L-07 – sikkerhedsnyhed

Kør admin `/news refresh` mod det valgte officielle feed. Kontrollér original link, dansk AI-resumé, kategori og deduplikering ved anden kørsel.

### L-08 – agentisk request

Kør `/assistant Hvad skal vi nå den næste uge, og hvilket af vores materialer forklarer emnet?`.

**Bestået:** Agenten vælger mindst deadline- og document-tool, viser kilder og foretager ingen ændring.

### L-09 – to samtidige AI-kald

To brugere kører `/ask` næsten samtidig.

**Bestået:** Begge får svar eller klar køstatus; botten crasher ikke.

## 6. Krav til test/evidens

- Gem ikke screenshots med tokens, private kanaler, persondata eller medlemsliste.
- Til demo er et screenshot af anonymiseret command/resultat nok som backup, men live funktion foretrækkes.
- Notér versionsnumre for Python, Ollama, modeller og dependencies.
- Notér den konkrete PDF-titel og licens/tilladelse.
- Notér kendte begrænsninger ærligt.

## 7. Release gate

`v0.1.0` må kun tagges, når:

- alle A-01–A-28 er grønne
- L-01–L-06 er dokumenteret bestået
- dependency audit er kørt og findings er håndteret/dokumenteret
- `.env`, DB, dokumenter, backups og logs er untracked
- backup er taget og restore-procedure er læst
- manual og faktisk adfærd er enige

