# Demo-runbook

## 1. Mål

Vis på 4–6 minutter, at SecMate bruger ekstern faglig kilde, husker mellem brug, deles af mindst to personer og arbejder proaktivt. Nyheder og `/assistant` vises kun, hvis de er stabile.

## 2. Dagen før

- [ ] Kør hele testsuiten og doctor.
- [ ] Kontrollér, at den valgte PDF må bruges og ikke har persondata.
- [ ] Vælg et spørgsmål med svar på en kendt side.
- [ ] Opret én ufølsom test-memory og én test-deadline.
- [ ] Genstart og bekræft persistence.
- [ ] Test digest uden dublet.
- [ ] Test to Discord-brugere.
- [ ] Tag verificeret DB-backup.
- [ ] Kontrollér `.env`/DB/docs/logs ikke er i git.
- [ ] Tag anonymiserede screenshots af succesfulde outputs som nødplan.
- [ ] Notér præcis Python-, Ollama- og modelversion.

## 3. 30 minutter før

1. Tilslut strøm og stabilt internet på host.
2. Luk tunge spil/programmer.
3. Start Ollama.
4. Aktivér `.venv`.
5. Kør `python scripts/doctor.py`.
6. Start `python -m secmate`.
7. Kør `/health` i statuskanalen.
8. Kør ét kendt `/ask`-spørgsmål.
9. Lad terminalen være synlig uden secrets eller personlige stier.

## 4. Live rækkefølge

### Trin 1 – fælles system

Person A kører `/health`. Forklar med egne ord, at alle bruger samme Discord-bot, mens backend, database og AI kører på én host.

### Trin 2 – ekstern kilde

Person B kører det kendte `/ask`-spørgsmål. Vis filnavn og korrekt side. Åbn PDF'en på siden, hvis tiden tillader det.

### Trin 3 – hukommelse

Vis `/memories`. Forklar, at noten blev gemt før genstart. Hvis læreren vil se det live, tilføj en ny ufølsom note, genstart kun hvis tidsplanen tillader det, og vis den igen.

### Trin 4 – praktisk/proaktiv

Vis `/deadlines list` og dagens automatiske digest i Discord. Forklar, at unique job-run i SQLite forhindrer dobbelte opslag efter genstart.

### Trin 5 – valgfri nyhed/agent

Hvis stabilt: vis én sikkerhedsnyhed med original kilde og kategori. Alternativt kør `/assistant` med kombineret deadline/dokumentspørgsmål.

## 5. Hvad I bør kunne forklare med egne ord

- Discord er cloud-delen; beskeder går gennem Discord.
- Bot, dokumenter, SQLite, embeddings og AI kører lokalt.
- `qwen3:4b` skriver svar; `embeddinggemma` finder relevante dokumentuddrag.
- SQLite husker fælles noter/deadlines mellem genstarter.
- Slash commands betyder, at botten ikke læser alle kanalbeskeder.
- Ingen cloud-AI betyder ingen betaling pr. prompt og mindre tredjepartsdeling.
- Host-computeren er single point of failure og skal være tændt.
- AI kan tage fejl; derfor kræves kildehenvisning og no-evidence fallback.

## 6. Nødplan

| Fejl | Gør dette |
|---|---|
| Internet/Discord nede | Vis screenshots + doctor + lokal testsuite; forklar ekstern afhængighed |
| Ollama nede | Vis deterministic `/deadlines list`/`/memories`, start Ollama, brug screenshot af `/ask` |
| Model langsom | Vent én gang; brug derefter screenshot og forklar lokal hardwarebegrænsning |
| PDF retrieval fejler | Vis kendt testresultat/screenshot og åbn `LIVE_TEST_RESULTS.md`; lov ikke falsk succes |
| Feed nede | Skip nyheder; minimumskravene ligger i docs/RAG/memory/shared setup |
| Databaseproblem | Stop bot; brug seneste verificerede backup; kør doctor før restart |

Nødplanen skal være ærlig: sig, hvad der virker nu, og hvad der blev verificeret tidligere.

## 7. Efter demo

- Slet unødvendig demo-memory/deadline.
- Stop botten, hvis andre ikke skal bruge den.
- Rotér token, hvis det kunne ses på skærm eller blev delt forkert.
- Bevar kode/testevidens; behold kun data efter de aftalte retention-regler.

