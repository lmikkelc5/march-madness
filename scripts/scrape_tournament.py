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
    return seeds_df


def main():
    pass


if __name__ == "__main__":
    main()
