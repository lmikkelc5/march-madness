import re
import sqlite3
from datetime import datetime

import pandas as pd
from bs4 import BeautifulSoup

from scripts.http_utils import polite_get
from scripts.get_schools_list import save_to_db
from scripts.checkpoint import is_done, mark_done
from config import DB_FILE

BOX_SCORE_STAT_COLUMNS = {
    "pts": "points",
    "fg": "fg",
    "fga": "fga",
    "fg_pct": "fg_pct",
    "fg3": "three_pt",
    "fg3a": "three_pt_attempts",
    "fg3_pct": "three_pt_pct",
    "ft": "ft",
    "fta": "fta",
    "ft_pct": "ft_pct",
    "orb": "offensive_rebounds",
    "trb": "total_rebounds",
    "ast": "assists",
    "stl": "steals",
    "blk": "blocks",
    "tov": "turnovers",
    "pf": "personal_fouls",
}


def _parse_value(raw):
    if raw in ("", None):
        return None
    try:
        return int(raw)
    except ValueError:
        try:
            return float(raw)
        except ValueError:
            return None


def _parse_overtimes(raw):
    raw = raw.strip()
    if not raw:
        return 0
    if raw == "OT":
        return 1
    match = re.match(r"(\d+)OT", raw)
    return int(match.group(1)) if match else 0


def _parse_date(raw):
    return datetime.strptime(raw, "%a, %b %d, %Y").strftime("%Y-%m-%d")


def get_team_schedule(team_slug, season):
    """One team's full game-by-game record for a season."""
    url = f"https://www.sports-reference.com/cbb/schools/{team_slug}/men/{season}-schedule.html"
    response = polite_get(url)
    soup = BeautifulSoup(response.text, "lxml")

    table = soup.select_one("#schedule")
    if table is None:
        return []

    games = []
    for tr in table.select("tbody tr"):
        boxscore_link = tr.select_one('td[data-stat="date_game"] a')
        opp_link = tr.select_one('td[data-stat="opp_name"] a')
        if boxscore_link is None or opp_link is None:
            continue

        cells = {td.get("data-stat"): td.get_text(strip=True) for td in tr.find_all("td")}

        games.append({
            "boxscore_slug": boxscore_link["href"].split("/")[-1].removesuffix(".html"),
            "date": _parse_date(cells["date_game"]),
            "game_type": cells["game_type"],
            "location": cells["game_location"],
            "opponent_slug": opp_link["href"].split("/")[-3],
            "pts": _parse_value(cells["pts"]),
            "opp_pts": _parse_value(cells["opp_pts"]),
            "overtimes": _parse_overtimes(cells["overtimes"]),
        })

    return games


def build_games_for_season(season, db_file=DB_FILE, team_slugs=None):
    """Scrape every active team's schedule and build the canonical `games` table for a season.

    `team_slugs` restricts which teams' schedules get scraped (for testing on
    a small scale); defaults to every team active that season.
    """
    with sqlite3.connect(db_file) as connection:
        team_id_map = dict(connection.execute("SELECT slug, team_id FROM teams").fetchall())
        if team_slugs is None:
            team_slugs = [
                row[0] for row in connection.execute(
                    "SELECT t.slug FROM teams t JOIN team_seasons ts ON ts.team_id = t.team_id WHERE ts.season = ?",
                    (season,),
                ).fetchall()
            ]
        conference_map = dict(connection.execute(
            "SELECT team_id, conference_id FROM team_conferences WHERE season = ?", (season,),
        ).fetchall())

    games_by_slug = {}

    for i, team_slug in enumerate(team_slugs, start=1):
        if i == 1 or i % 25 == 0 or i == len(team_slugs):
            print(f"  [{season}] schedule {i}/{len(team_slugs)}: {team_slug}", flush=True)

        team_id = team_id_map[team_slug]
        for game in get_team_schedule(team_slug, season):
            opponent_id = team_id_map.get(game["opponent_slug"])
            if opponent_id is None:
                print(f"Skipping game vs unknown team slug '{game['opponent_slug']}' ({team_slug} {season})")
                continue

            is_neutral = game["location"] == "N"
            if game["location"] == "@":
                home_id, away_id = opponent_id, team_id
                home_score, away_score = game["opp_pts"], game["pts"]
            elif game["location"] == "":
                home_id, away_id = team_id, opponent_id
                home_score, away_score = game["pts"], game["opp_pts"]
            else:
                # Neutral site: order deterministically so both teams'
                # schedule rows for this game agree on the assignment.
                if team_id < opponent_id:
                    home_id, away_id = team_id, opponent_id
                    home_score, away_score = game["pts"], game["opp_pts"]
                else:
                    home_id, away_id = opponent_id, team_id
                    home_score, away_score = game["opp_pts"], game["pts"]

            is_conference_game = (
                game["game_type"] == "REG"
                and conference_map.get(team_id) is not None
                and conference_map.get(team_id) == conference_map.get(opponent_id)
            )

            games_by_slug[game["boxscore_slug"]] = {
                "boxscore_slug": game["boxscore_slug"],
                "season": season,
                "date": game["date"],
                "home_team_id": home_id,
                "away_team_id": away_id,
                "home_score": home_score,
                "away_score": away_score,
                "is_neutral_site": int(is_neutral),
                "overtimes": game["overtimes"],
                "is_conference_game": int(is_conference_game),
                "is_tournament_game": int(game["game_type"] == "NCAA"),
            }

    games_df = pd.DataFrame(games_by_slug.values())
    if not games_df.empty:
        save_to_db(games_df, "games", "boxscore_slug", db_file)

    return games_df


def get_game_box_score(boxscore_slug):
    """Team-totals box score stats for both teams in one game, keyed by team slug."""
    url = f"https://www.sports-reference.com/cbb/boxscores/{boxscore_slug}.html"
    response = polite_get(url)
    soup = BeautifulSoup(response.text, "lxml")

    stats_by_team_slug = {}
    for table in soup.select('table[id^="box-score-basic-"]'):
        team_slug = table["id"].removeprefix("box-score-basic-")
        totals_row = table.select_one("tfoot tr")
        if totals_row is None:
            continue

        stats = {}
        for cell in totals_row.find_all(["td", "th"]):
            column = BOX_SCORE_STAT_COLUMNS.get(cell.get("data-stat"))
            if column:
                stats[column] = _parse_value(cell.get_text(strip=True))

        stats_by_team_slug[team_slug] = stats

    return stats_by_team_slug


def build_team_game_stats_for_season(season, db_file=DB_FILE):
    """Fetch the box score for every game in a season and populate team_game_stats.

    Expensive: one request per game. Checkpointed per game (not just per
    season) so an interrupted run resumes without refetching completed games.
    """
    with sqlite3.connect(db_file) as connection:
        team_id_map = dict(connection.execute("SELECT slug, team_id FROM teams").fetchall())
        games = connection.execute(
            "SELECT game_id, boxscore_slug, home_team_id, away_team_id FROM games WHERE season = ?",
            (season,),
        ).fetchall()

    slug_to_team_id = team_id_map
    team_id_to_slug = {v: k for k, v in team_id_map.items()}

    total = len(games)
    for i, (game_id, boxscore_slug, home_team_id, away_team_id) in enumerate(games, start=1):
        if i == 1 or i % 50 == 0 or i == total:
            print(f"  [{season}] box score {i}/{total}: {boxscore_slug}", flush=True)

        checkpoint_key = f"box_score:{boxscore_slug}"
        if is_done("results", checkpoint_key):
            continue

        stats_by_slug = get_game_box_score(boxscore_slug)

        rows = []
        for team_id, opponent_id in ((home_team_id, away_team_id), (away_team_id, home_team_id)):
            team_slug = team_id_to_slug.get(team_id)
            stats = stats_by_slug.get(team_slug)
            if stats is None:
                print(f"Missing box score stats for team '{team_slug}' in game {boxscore_slug}")
                continue
            rows.append({"game_id": game_id, "team_id": team_id, "opponent_id": opponent_id, **stats})

        if rows:
            save_to_db(pd.DataFrame(rows), "team_game_stats", ("game_id", "team_id"), db_file)

        mark_done("results", checkpoint_key)


def main():
    pass


if __name__ == "__main__":
    main()
