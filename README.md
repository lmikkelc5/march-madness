# March Madness Prediction

An attempt at predicting future NCAA March Madness tournament outcomes from historical data. Team, conference, and game data is scraped from [sports-reference.com](https://www.sports-reference.com/cbb/) into a local SQLite database, spanning multiple past seasons, so a prediction model can eventually be trained on several years of history and backtested against real tournament outcomes.

The project is in active development. The scraping pipeline (this README's focus) is functional; the prediction model itself hasn't been started yet.

## Requirements

- Python 3.13 (see `.python-version`)
- [`uv`](https://docs.astral.sh/uv/) for dependency management

```bash
uv sync
```

There is no test suite, linter, or formatter configured yet.

## How the pipeline is organized

There's no single "run everything" script. Scraping is split into **tiers** by how often the underlying data actually changes, and each tier has its own runner script that loops over a range of seasons:

| Tier | Script | What it populates | Cadence |
|---|---|---|---|
| Schema setup | `scripts/init_db.py` | Creates/wipes the whole schema | Once, or after a schema change |
| Roster | `scripts/update_roster.py` | `teams`, `team_seasons`, `conferences`, `team_conferences` | Once per season |
| Results | `scripts/update_results.py` | `games`, `team_game_stats` | Once the season/tournament is over |
| *(planned)* | — | `rankings`, `injuries` | Weekly / as it changes during the season |

Every script other than `init_db.py` only inserts or upserts data — none of them ever delete anything — so they're always safe to re-run. Re-running just refreshes whatever season/table you point them at.

### Running it

**1. First-time setup** — creates `database/march_madness.db` from scratch. **Destructive** (wipes any existing data), only run this once or after a schema change:

```bash
uv run python -m scripts.init_db
```

**2. Backfill the roster tier** for a season range (teams, season stats, conference membership):

```bash
uv run python -m scripts.update_roster --start-season 2023 --end-season 2025
```

**3. Backfill the results tier** (must run *after* the roster tier for the same seasons, since games depend on `team_conferences` to flag conference games, and on `team_seasons` to know which teams were active that season):

```bash
uv run python -m scripts.update_results --start-season 2023 --end-season 2025
```

`update_results` has two steps: `games` (cheap — one request per team per season) and `team_game_stats` (expensive — one request per *individual game*, since full box-score shooting splits only live on each game's own box-score page). Run just one step with `--steps`:

```bash
uv run python -m scripts.update_results --start-season 2023 --end-season 2025 --steps games
uv run python -m scripts.update_results --start-season 2023 --end-season 2025 --steps team_game_stats
```

**Re-running / resuming**: both runners checkpoint progress to JSON files under `state/` (via `scripts/checkpoint.py`), keyed by `"{season}:{step}"` — `update_results` additionally checkpoints `team_game_stats` **per individual game**, since that step alone can take hours for a single season. If a run is interrupted (closed terminal, machine sleep, crash), just run the exact same command again — completed work is skipped automatically. Pass `--force` to redo something anyway.

### Timing expectations

Every scraper is rate-limited (see `scripts/http_utils.py`) to stay under sports-reference.com's throttling, at roughly one request per 3 seconds. Rough costs per season:

- Roster tier: ~100-110 seconds (a couple dozen requests)
- Results tier, `games` step: ~15-20 minutes (~360 teams, one request each)
- Results tier, `team_game_stats` step: **~2+ hours** (~5,000 individual game box scores)

A full 10-15 season backfill including box scores is realistically a 30-45+ hour undertaking. Background runs on a local machine don't survive a shutdown or closed terminal (they do usually survive the machine sleeping) — but thanks to checkpointing, resuming after an interruption just means re-running the same command.

## Database schema

Defined in `scripts/create_database.py`. `config.py` defines `DB_FILE` (the database path) and `STATE_DIR` (checkpoint state directory) — every script imports these rather than hardcoding paths. `season` is a plain integer column throughout (not a separate database per year), so multiple seasons of history live side by side in the same tables — this is what makes a later `WHERE season < 2024` (train) vs `WHERE season = 2024` (backtest) split possible.

**Built and populated:**
- **`teams`** — `team_id`, `school`, `slug` (URL-safe name, upsert key), `url`.
- **`team_seasons`** — one row per team per season (`UNIQUE(team_id, season)`). Record (`games`, `wins`, `losses`, `win_pct`), rating metrics (`srs`, `sos`), scoring (`points`, `opponent_points` — **season totals**, not per-game averages; divide by `games` if you want per-game), and full box-score totals (shooting splits, rebounds, assists, steals, blocks, turnovers, fouls). Has a `coach_id` FK for later use.
- **`conferences`** — `conference_id`, `name`, `slug`. Scraped per-season (not from a static list), since conference names/slugs change with realignment year to year.
- **`team_conferences`** — team↔conference membership per season (`UNIQUE(team_id, season)`) — season-scoped rather than a column on `teams`, because teams change conferences.
- **`games`** — one canonical row per physical game (`UNIQUE` on `boxscore_slug`, sports-reference's own game identifier — needed because two teams can play each other more than once a season, so date+opponent alone isn't a safe key). Home/away teams and scores, neutral-site flag, overtimes, and whether it was a conference game or NCAA tournament game.
- **`team_game_stats`** — one row per team per game (`UNIQUE(game_id, team_id)`), with full shooting/rebounding/box-score totals for that single game, sourced from the individual box-score page.

**Schema exists, no scraper built yet:**
- **`coaches`**, **`players`**, **`player_seasons`** — player-level season stats.
- **`injuries`** — time-boxed injury events per player. Deliberately deferred: sports-reference doesn't track injuries at all, so this needs a different data source.
- **`rankings`** — weekly AP Poll / NET rankings per team.
- **`tournament_seeds`** — seed/region per team per NCAA tournament appearance.
- **`seasons`** — season-level metadata (champion, runner-up, tournament field size).

## `scripts/` reference

### `scripts/http_utils.py`
`polite_get(url)` — the only way any scraper should make an HTTP request. Enforces a minimum delay between requests and retries with exponential backoff on a 429. Every scraper routes through this to avoid getting rate-limited or blocked by sports-reference.com.

### `scripts/checkpoint.py`
`is_done(job_name, key)` / `mark_done(job_name, key)` — a tiny JSON-file-backed "have I already done this?" tracker, stored under `state/<job_name>.json`. Used by both runner scripts so interrupted backfills resume instead of restarting.

### `scripts/create_database.py`
`create_database(db_file)` builds the full schema (see above). `delete_database(db_file)` removes the `.db` file if it exists. Only ever called from `scripts/init_db.py`.

### `scripts/init_db.py`
CLI wrapper: `delete_database()` + `create_database()`. The only destructive script in the project.

### `scripts/get_schools_list.py`
`get_schools_list(url)` scrapes a sports-reference season-stats page for the list of D-I schools (name, slug, url). Also defines `save_to_db(df, table_name, conflict_columns, db_file=DB_FILE)`, the shared upsert helper used by *every* scraper in the project — it builds an `INSERT ... ON CONFLICT(...) DO UPDATE SET ...` statement from a DataFrame's columns, so re-running a scrape updates existing rows instead of duplicating them.

### `scripts/scrape_team_stats.py`
`scrape_team_stats(season)` parses the season school-stats table directly via BeautifulSoup, keyed by each cell's `data-stat` attribute (rather than `pandas.read_html`, which misaligns rows because sports-reference periodically repeats header rows in long tables). `scrape_and_save_team_seasons(season, db_file)` resolves each row's team slug to a `team_id` and upserts into `team_seasons`.

### `scripts/scrape_conferences.py`
`get_conferences_list(season)` scrapes that season's conference-summary table (season-specific, since conference names/slugs change over time). `get_conference_team_slugs(conference_slug, season)` scrapes one conference's member schools for that season. `scrape_conferences_and_memberships(season, db_file)` ties both together and upserts `conferences` + `team_conferences`.

### `scripts/scrape_games.py`
- `get_team_schedule(team_slug, season)` scrapes one team's full schedule/results page for a season.
- `build_games_for_season(season, db_file, team_slugs=None)` scrapes every active team's schedule (or a subset, via `team_slugs`, useful for testing) and builds the deduplicated `games` table, working out home/away/scores/conference-game/tournament-game flags from each row.
- `get_game_box_score(boxscore_slug)` scrapes one individual game's box score page for both teams' full stat lines.
- `build_team_game_stats_for_season(season, db_file)` fetches the box score for every game in a season and populates `team_game_stats`, checkpointing per game.

### `scripts/update_roster.py` / `scripts/update_results.py`
The CLI runners described above — loop a season range, run each tier's steps, checkpoint as they go, and print a summary of any failed steps at the end (safe to just rerun the same command to retry them).

### `main.py`
Unused template placeholder, not part of the actual pipeline.

## `src/march madness/`

Empty scaffolding (`constants.py`, `database.py`, `models.py`, `scraper.py`) for a possible future restructure of `scripts/` into an installable package. Note the space in the directory name (`march madness`, not `march_madness`) — this needs to be fixed before it could work as an importable Python package. Nothing here is wired up yet.

## Looking at the data

- **VSCode**: install the "SQLite Viewer" extension and click `database/march_madness.db` in the file explorer.
- **DB Browser for SQLite** ([sqlitebrowser.org](https://sqlitebrowser.org/)): a free standalone GUI.
- **CLI**: `sqlite3 database/march_madness.db`, then `.tables`, `.schema teams`, or any `SELECT ...` query.
