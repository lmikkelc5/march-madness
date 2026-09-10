import sqlite3

import pandas as pd
from bs4 import BeautifulSoup

from scripts.http_utils import polite_get
from scripts.get_schools_list import save_to_db
from config import DB_FILE


def get_conferences_list(season):
    """D-I conferences active in a given season (name + slug).

    Scraped from the season summary page rather than the global conference
    index, since conference slugs and names change across seasons
    (realignment/rebranding) and the index only reflects the current year.
    """
    url = f"https://www.sports-reference.com/cbb/seasons/men/{season}.html"
    response = polite_get(url)
    soup = BeautifulSoup(response.text, "lxml")

    conferences = []
    for a in soup.select('#conference-summary td[data-stat="conf_name"] a'):
        href = a["href"]
        conferences.append({
            "name": a.text.strip(),
            "slug": href.split("/")[-3],
        })

    return pd.DataFrame(conferences)


def get_conference_team_slugs(conference_slug, season):
    """Team slugs that were members of one conference in one season."""
    url = f"https://www.sports-reference.com/cbb/conferences/{conference_slug}/men/{season}.html"
    response = polite_get(url)
    soup = BeautifulSoup(response.text, "lxml")

    return [
        a["href"].split("/")[-3]
        for a in soup.select('td[data-stat="school_name"] a')
    ]


def get_slug_id_map(table_name, id_column, db_file=DB_FILE):
    with sqlite3.connect(db_file) as connection:
        rows = connection.execute(f'SELECT slug, "{id_column}" FROM "{table_name}"').fetchall()
    return dict(rows)


def build_team_conferences(season, conferences_df, db_file=DB_FILE):
    """Team<->conference membership for one season, as a DataFrame ready for save_to_db."""
    conference_id_map = get_slug_id_map("conferences", "conference_id", db_file)
    team_id_map = get_slug_id_map("teams", "team_id", db_file)

    memberships = []
    for _, row in conferences_df.iterrows():
        team_slugs = get_conference_team_slugs(row["slug"], season)
        for team_slug in team_slugs:
            if team_slug not in team_id_map:
                print(f"Skipping unknown team slug '{team_slug}' ({row['slug']} {season})")
                continue
            memberships.append({
                "team_id": team_id_map[team_slug],
                "conference_id": conference_id_map[row["slug"]],
                "season": season,
            })

    return pd.DataFrame(memberships)


def scrape_conferences_and_memberships(season, db_file=DB_FILE):
    conferences_df = get_conferences_list(season)
    save_to_db(conferences_df, "conferences", "slug", db_file)

    memberships_df = build_team_conferences(season, conferences_df, db_file)
    save_to_db(memberships_df, "team_conferences", ("team_id", "season"), db_file)

    return conferences_df, memberships_df


def main():
    pass


if __name__ == "__main__":
    main()
