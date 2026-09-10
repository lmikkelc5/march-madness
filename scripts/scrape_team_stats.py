import sqlite3

import pandas as pd
from bs4 import BeautifulSoup

from scripts.http_utils import polite_get
from scripts.get_schools_list import save_to_db
from config import DB_FILE

# data-stat attribute -> team_seasons column. Parsed directly from each row's
# cells (rather than pandas.read_html) because sports-reference repeats the
# header row periodically in long tables, which throws off read_html's row
# count relative to the actual number of teams.
STAT_COLUMNS = {
    "g": "games",
    "wins": "wins",
    "losses": "losses",
    "win_loss_pct": "win_pct",
    "srs": "srs",
    "sos": "sos",
    "pts": "points",
    "opp_pts": "opponent_points",
    "mp": "minutes",
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


def scrape_team_stats(season):
    """Season-total team stats for every school, keyed by team slug."""
    url = f"https://www.sports-reference.com/cbb/seasons/men/{season}-school-stats.html"
    response = polite_get(url)
    soup = BeautifulSoup(response.text, "lxml")

    rows = []
    for tr in soup.select("table tbody tr"):
        school_cell = tr.select_one('td[data-stat="school_name"] a')
        if school_cell is None:
            continue

        row = {"slug": school_cell["href"].split("/")[-3], "season": season}
        for cell in tr.find_all("td"):
            column = STAT_COLUMNS.get(cell.get("data-stat"))
            if column:
                row[column] = _parse_value(cell.get_text(strip=True))

        rows.append(row)

    return pd.DataFrame(rows)


def scrape_and_save_team_seasons(season, db_file=DB_FILE):
    stats_df = scrape_team_stats(season)

    with sqlite3.connect(db_file) as connection:
        slug_to_team_id = dict(connection.execute('SELECT slug, team_id FROM teams').fetchall())

    stats_df["team_id"] = stats_df["slug"].map(slug_to_team_id)

    unmatched = stats_df[stats_df["team_id"].isna()]
    for slug in unmatched["slug"]:
        print(f"Skipping unknown team slug '{slug}' ({season})")

    stats_df = stats_df.dropna(subset=["team_id"]).drop(columns=["slug"])
    stats_df["team_id"] = stats_df["team_id"].astype(int)

    save_to_db(stats_df, "team_seasons", ("team_id", "season"), db_file)
    return stats_df


def main():
    pass


if __name__ == "__main__":
    main()
