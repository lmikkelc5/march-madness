import sqlite3

import pandas as pd
from bs4 import BeautifulSoup

from scripts.http_utils import polite_get
from scripts.get_schools_list import save_to_db
from config import DB_FILE


def get_tournament_seeds(season):
    """Seed + region for every team in one season's NCAA tournament field.

    Sports-reference's bracket page nests each region as a div (id "east",
    "midwest", etc.) containing a round-of-64 round where each team's seed
    and school link sit together - First Four winners are already folded
    into that round, so this reflects the final 64-team field directly.
    """
    url = f"https://www.sports-reference.com/cbb/postseason/men/{season}-ncaa.html"
    response = polite_get(url)
    soup = BeautifulSoup(response.text, "lxml")

    seeds = []
    for region_div in soup.select("#brackets > div[id]"):
        # The "national" div holds the Final Four/championship bracket
        # (regional champions advancing), not an actual region - skip it,
        # or its bogus region value overwrites the real one on upsert.
        if region_div["id"] == "national":
            continue

        first_round = region_div.select_one(".round")
        if first_round is None:
            continue

        for game_div in first_round.find_all("div", recursive=False):
            for team_div in game_div.find_all("div", recursive=False):
                seed_span = team_div.find("span")
                team_link = team_div.find("a")
                if seed_span is None or team_link is None:
                    continue
                seed_text = seed_span.get_text(strip=True)
                if not seed_text.isdigit():
                    continue

                seeds.append({
                    "slug": team_link["href"].split("/")[-3],
                    "season": season,
                    "seed": int(seed_text),
                    "region": region_div["id"].capitalize(),
                })

    return pd.DataFrame(seeds)


def scrape_and_save_tournament_seeds(season, db_file=DB_FILE):
    seeds_df = get_tournament_seeds(season)

    with sqlite3.connect(db_file) as connection:
        slug_to_team_id = dict(connection.execute("SELECT slug, team_id FROM teams").fetchall())

    seeds_df["team_id"] = seeds_df["slug"].map(slug_to_team_id)

    unmatched = seeds_df[seeds_df["team_id"].isna()]
    for slug in unmatched["slug"]:
        print(f"Skipping unknown team slug '{slug}' ({season})")

    seeds_df = seeds_df.dropna(subset=["team_id"]).drop(columns=["slug"])
    seeds_df["team_id"] = seeds_df["team_id"].astype(int)

    save_to_db(seeds_df, "tournament_seeds", ("team_id", "season"), db_file)
    fill_first_four_loser_seeds(season, db_file)
    return seeds_df


def fill_first_four_loser_seeds(season, db_file=DB_FILE):
    """Give First Four losers the seed/region of the team that beat them.

    The bracket page's round of 64 only lists First Four winners, so the 4
    losers each year never get a seed from get_tournament_seeds. First Four
    games are always between two teams on the same seed line in the same
    region, so the winner's seed/region is the loser's too. Needs the
    `games` step to have run for this season.
    """
    with sqlite3.connect(db_file) as connection:
        rows = connection.execute(
            """
            SELECT
                CASE WHEN g.home_score > g.away_score THEN g.away_team_id ELSE g.home_team_id END AS loser_id,
                s.seed, s.region
            FROM games g
            JOIN tournament_seeds s
              ON s.season = g.season
             AND s.team_id = CASE WHEN g.home_score > g.away_score THEN g.home_team_id ELSE g.away_team_id END
            WHERE g.season = ? AND g.is_tournament_game = 1
              AND NOT EXISTS (
                  SELECT 1 FROM tournament_seeds s2
                  WHERE s2.season = g.season
                    AND s2.team_id = CASE WHEN g.home_score > g.away_score THEN g.away_team_id ELSE g.home_team_id END
              )
            """,
            (season,),
        ).fetchall()

    if rows:
        losers_df = pd.DataFrame(rows, columns=["team_id", "seed", "region"])
        losers_df["season"] = season
        save_to_db(losers_df, "tournament_seeds", ("team_id", "season"), db_file)
    return len(rows)


# Rounds after the First Four, in order, with how many games each has.
MAIN_BRACKET_ROUNDS = [
    ("Round of 64", 32),
    ("Round of 32", 16),
    ("Sweet 16", 8),
    ("Elite 8", 4),
    ("Final Four", 2),
    ("Championship", 1),
]
REGIONAL_ROUNDS = {"First Four", "Round of 64", "Round of 32", "Sweet 16", "Elite 8"}


def assign_tournament_rounds(season, db_file=DB_FILE):
    """Fill games.round and games.region for one season's tournament games.

    Rounds never share a date, so sorting the games by date and counting
    from the end (1 championship, 2 Final Four, 4 Elite 8, ...) labels them
    exactly. Anything before the 63 main-bracket games is a First Four game.
    Region comes from tournament_seeds (both teams share it through the
    Elite 8); Final Four and Championship games get no region. Needs the
    `games` and `tournament_seeds` steps to have run for this season.
    """
    with sqlite3.connect(db_file) as connection:
        games = connection.execute(
            """
            SELECT g.game_id, g.date, s.region
            FROM games g
            LEFT JOIN tournament_seeds s ON s.season = g.season AND s.team_id = g.home_team_id
            WHERE g.season = ? AND g.is_tournament_game = 1
            ORDER BY g.date, g.game_id
            """,
            (season,),
        ).fetchall()

        main_bracket_size = sum(count for _, count in MAIN_BRACKET_ROUNDS)
        if len(games) < main_bracket_size:
            print(f"Skipping rounds for {season}: only {len(games)} tournament games (expected at least {main_bracket_size})")
            return 0

        rounds = ["First Four"] * (len(games) - main_bracket_size)
        for round_name, count in MAIN_BRACKET_ROUNDS:
            rounds += [round_name] * count

        # If a date ends up split across two rounds, a game is missing or extra.
        rounds_by_date = {}
        for (_, date, _), round_name in zip(games, rounds):
            rounds_by_date.setdefault(date, set()).add(round_name)
        mixed_dates = [date for date, names in rounds_by_date.items() if len(names) > 1]
        if mixed_dates:
            print(f"Skipping rounds for {season}: dates {mixed_dates} span more than one round, check for missing games")
            return 0

        connection.executemany(
            "UPDATE games SET round = ?, region = ? WHERE game_id = ?",
            [
                (round_name, region if round_name in REGIONAL_ROUNDS else None, game_id)
                for (game_id, _, region), round_name in zip(games, rounds)
            ],
        )
    return len(games)


def main():
    pass


if __name__ == "__main__":
    main()
