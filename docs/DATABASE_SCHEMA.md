# SQLite-datamodel

## 1. Generelle regler

- Nummererede SQL-migrations i `migrations/`.
- Migrationer køres ved startup i transaction og registreres i `schema_migrations`.
- `PRAGMA foreign_keys=ON`, `journal_mode=WAL`, `busy_timeout=5000`.
- Alle timestamps er ISO-8601 UTC tekst med `Z` eller integer epoch; vælg én form konsekvent. Denne specifikation foretrækker ISO-8601 UTC.
- Offentlige IDs er tilfældige UUIDv4/ULID-lignende strings, ikke let gættelige row numbers.
- Ingen tabel indeholder Discord user ID, brugernavn, e-mail eller samtalehistorik.

## 2. Tabeller

### `schema_migrations`

| Kolonne | Type/regler |
|---|---|
| `version` | INTEGER PRIMARY KEY |
| `name` | TEXT NOT NULL |
| `applied_at_utc` | TEXT NOT NULL |

### `guild_settings`

| Kolonne | Type/regler |
|---|---|
| `guild_id` | TEXT PRIMARY KEY |
| `timezone` | TEXT NOT NULL DEFAULT `Europe/Copenhagen` |
| `digest_channel_id` | TEXT NULL |
| `digest_time_local` | TEXT NOT NULL |
| `news_time_local` | TEXT NOT NULL |
| `created_at_utc` | TEXT NOT NULL |
| `updated_at_utc` | TEXT NOT NULL |

Kanal-ID'er er routingmetadata. Konfiguration kan initialt komme fra `.env` og sync'es deterministisk til denne række.

### `memories`

| Kolonne | Type/regler |
|---|---|
| `id` | TEXT PRIMARY KEY |
| `guild_id` | TEXT NOT NULL |
| `content` | TEXT NOT NULL, længdevalideret |
| `created_at_utc` | TEXT NOT NULL |
| `expires_at_utc` | TEXT NOT NULL |

Index: `(guild_id, expires_at_utc)`.

### `deadlines`

| Kolonne | Type/regler |
|---|---|
| `id` | TEXT PRIMARY KEY |
| `guild_id` | TEXT NOT NULL |
| `title` | TEXT NOT NULL |
| `due_at_utc` | TEXT NOT NULL |
| `status` | TEXT NOT NULL CHECK `pending/completed` |
| `created_at_utc` | TEXT NOT NULL |
| `completed_at_utc` | TEXT NULL |

Index: `(guild_id, status, due_at_utc)`.

### `documents`

| Kolonne | Type/regler |
|---|---|
| `id` | TEXT PRIMARY KEY |
| `display_name` | TEXT NOT NULL |
| `relative_path` | TEXT NOT NULL UNIQUE |
| `sha256` | TEXT NOT NULL |
| `file_type` | TEXT NOT NULL |
| `page_count` | INTEGER NULL |
| `embed_model` | TEXT NOT NULL |
| `indexed_at_utc` | TEXT NOT NULL |

Unique: `(relative_path, sha256, embed_model)` eller en tilsvarende idempotent strategi.

### `document_chunks`

| Kolonne | Type/regler |
|---|---|
| `id` | TEXT PRIMARY KEY |
| `document_id` | TEXT NOT NULL REFERENCES documents(id) ON DELETE CASCADE |
| `chunk_index` | INTEGER NOT NULL |
| `page_start` | INTEGER NULL |
| `page_end` | INTEGER NULL |
| `content` | TEXT NOT NULL |
| `embedding` | BLOB NOT NULL |
| `embedding_dimensions` | INTEGER NOT NULL |
| `embed_model` | TEXT NOT NULL |

Unique: `(document_id, chunk_index)`. Index: `document_id`.

### `news_items`

| Kolonne | Type/regler |
|---|---|
| `id` | TEXT PRIMARY KEY |
| `dedupe_key` | TEXT NOT NULL UNIQUE |
| `source_name` | TEXT NOT NULL |
| `title` | TEXT NOT NULL |
| `url` | TEXT NOT NULL |
| `published_at_utc` | TEXT NULL |
| `fetched_at_utc` | TEXT NOT NULL |
| `category` | TEXT NOT NULL CHECK tilladt enum |
| `summary_da` | TEXT NOT NULL |
| `study_relevance_da` | TEXT NOT NULL |
| `confidence` | REAL NULL CHECK 0..1 |
| `posted_at_utc` | TEXT NULL |
| `expires_at_utc` | TEXT NOT NULL |

`dedupe_key` = SHA-256 af canonicalized URL; hvis link mangler: source + stable entry ID + title.

### `job_runs`

| Kolonne | Type/regler |
|---|---|
| `id` | TEXT PRIMARY KEY |
| `job_name` | TEXT NOT NULL |
| `guild_id` | TEXT NOT NULL |
| `local_date` | TEXT NOT NULL (`YYYY-MM-DD`) |
| `status` | TEXT NOT NULL CHECK `claimed/succeeded/failed` |
| `attempts` | INTEGER NOT NULL DEFAULT 0 |
| `claimed_at_utc` | TEXT NOT NULL |
| `finished_at_utc` | TEXT NULL |
| `last_error_code` | TEXT NULL |

Unique: `(job_name, guild_id, local_date)`. Gem kun stabil fejlkode, ikke exceptiontekst med input.

## 3. Transaction-krav

- Reindex af én fil opretter/erstatter document + chunks atomisk. Et mislykket embed må ikke slette sidste fungerende indeks.
- Daily job claim bruger `INSERT` mod unique constraint i en transaction.
- Nyhedsitem gemmes før post; `posted_at_utc` sættes efter succes. Retry må ikke oprette nyt item.
- Deadline/memory writes valideres før transaction.
- Repositories returnerer domæneobjekter, ikke rå cursors.

## 4. Migrationstest

- tom database → latest schema
- kør migration to gange → ingen ændring/fejl
- simuler halv migration → rollback
- foreign keys og unique constraints virker
- eksisterende data bevares ved næste migration
- backupdatabase består `PRAGMA integrity_check`

