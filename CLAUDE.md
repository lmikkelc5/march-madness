# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project purpose

Predicting future March Madness (NCAA men's college basketball) tournament outcomes from historical data. Data is scraped from sports-reference.com, stored in a local SQLite database, and will eventually feed a prediction model trained/backtested across roughly 10-15 seasons of history. The project is in early, active development.

## Commands

This project uses `uv` for dependency management (Python 3.13, see `.python-version`).

- Install/sync dependencies: `uv sync`
- Initialize (or reset) the database schema: `uv run python -m scripts.init_db` — **destructive**, wipes and rebuilds `database/march_madness.db` from scratch. Only run for first-time setup or after a schema change in `create_database.py`.
- Backfill the roster tier for a season range: `uv run python -m scripts.update_roster --start-season 2020 --end-season 2025`

There is no test suite, linter, or formatter configured yet (no pytest/ruff/black config in `pyproject.toml`).

## Architecture

### Tiered pipeline, not a single script

There is no monolithic "run everything" entry point. Data is scraped by cadence tier, each with its own runner script that loops over a season range and checkpoints progress so a crash mid-run doesn't require starting over:

- **`scripts/init_db.py`** — the *only* script that deletes/recreates the schema. Every other script only inserts/upserts, so rerunning them is always safe.
- **`scripts/update_roster.py --start-season Y --end-season Y`** — the "once per season" tier: `teams`, `team_seasons`, `conferences`/`team_conferences`. Loops seasons, calling the scrapers in `scripts/get_schools_list.py`, `scripts/scrape_team_stats.py`, and `scripts/scrape_conferences.py`.
- **`scripts/update_results.py`** (planned) — the "once after the season ends" tier: `games`, `team_game_stats`, `tournament_seeds`.
- A future "frequent" tier will cover `rankings` (updates weekly during the season) and eventually `injuries` once a data source is picked (sports-reference doesn't track injuries).

Each tier script uses `scripts/checkpoint.py` (`is_done`/`mark_done`, backed by JSON files under `state/`) keyed by `"{season}:{step}"`, so re-running a tier script skips work already completed. Pass `--force` to redo anyway.

All HTTP requests go through `scripts/http_utils.polite_get()`, which enforces a minimum delay between requests and backs off on 429s — sports-reference throttles aggressively (~20 req/min). Any new scraper must use this instead of calling `requests.get` directly.

### Database (`config.py` / `database/march_madness.db`)

`config.py` defines `DB_FILE` (database path) and `STATE_DIR` (checkpoint state directory) — every script imports these rather than hardcoding paths.

Schema (defined in `scripts/create_database.py`), 13 tables:
- **`teams`**: `team_id`, `school`, `slug` (URL-safe name, upsert conflict key), `url`.
- **`team_seasons`**: one row per team per season (`UNIQUE(team_id, season)`). Record, `srs`/`sos`, scoring (`points`, `opponent_points` — season **totals**, not per-game averages; divide by `games` for per-game), full box-score totals, and a `coach_id` FK (not yet populated — no coach scraper built yet).
- **`conferences`**: `conference_id`, `name`, `slug`.
- **`team_conferences`**: team↔conference membership per season (`UNIQUE(team_id, season)`) — conference realignment means this must be season-scoped, not a column on `teams`.
- **`coaches`**, **`players`**, **`player_seasons`**, **`injuries`**: schema exists, no scrapers built yet.
- **`games`**, **`team_game_stats`**: schema exists for the results tier, no scraper built yet.
- **`rankings`**, **`tournament_seeds`**, **`seasons`**: schema exists, no scraper built yet.

### Scraping conventions (`scripts/`)

- Prefer parsing sports-reference tables directly via BeautifulSoup using each cell's `data-stat` attribute (see `scrape_team_stats.py`) rather than `pandas.read_html`. Sports-reference repeats header rows periodically in long tables, which throws off `read_html`'s row count relative to the actual number of teams — this caused a real bug (see `scrape_team_stats.py` history) where per-row data silently misaligned with team slugs.
- Conference (and other) slugs/names are **season-specific** — they change with realignment/rebranding year to year. Always scrape the season-specific summary page (e.g. `#conference-summary` on `seasons/men/{season}.html`) rather than a general/current-year index page when building historical data.
- `get_schools_list.save_to_db(df, table_name, conflict_columns, db_file=DB_FILE)` is the shared upsert helper used by all scrapers: it dynamically builds an `INSERT ... ON CONFLICT(...) DO UPDATE SET ...` statement from a DataFrame's columns, so re-running a scrape updates existing rows instead of duplicating them.
- Scrapers that need to resolve a `team_id`/`conference_id` from a scraped slug do so via a slug→id lookup against the already-populated table (see `get_slug_id_map` in `scrape_conferences.py`), not by assuming row order lines up across separate requests/parses.

### `src/march madness/`

Empty scaffolding (`constants.py`, `database.py`, `models.py`, `scraper.py`) for a possible future restructure of `scripts/` into an installable package. Note the space in the directory name (`march madness`, not `march_madness`) — this will need to be fixed before it can work as an importable Python package. Nothing here is wired up yet; don't assume it mirrors `scripts/`.

### `main.py`

Unused template placeholder, not part of the actual pipeline.
