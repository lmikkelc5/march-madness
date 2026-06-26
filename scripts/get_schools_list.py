from bs4 import BeautifulSoup
import pandas as pd
import requests
from pathlib import Path
import sqlite3

def get_schools_list():
    URL = "https://www.sports-reference.com/cbb/seasons/men/2026-school-stats.html"

    #get html content
    response = requests.get(URL, headers={"User-Agent": "Mozilla/5.0"})

    soup = BeautifulSoup(response.text, "lxml")

    teams = []

    #pull the data I want for the teams names, slugs, and urls
    for a in soup.select('td[data-stat="school_name"] a'):

        href = a["href"]

        teams.append({
            "school": a.text.strip(),
            "slug": href.split("/")[-3],
            "url": href
        })

    df = pd.DataFrame(teams)

    return df.head()

def save_to_db(df):
    #open database and add the data to the team table. 
    ROOT = Path(__file__).resolve().parent.parent

    DB_FILE = ROOT / "database" / "march_madness.db"

    with sqlite3.connect(DB_FILE) as connection:
        cursor = connection.cursor()

        cursor.executemany(
            """
            INSERT OR IGNORE INTO teams (school, slug, url)
            VALUES (?, ?, ?)
            """,
            df.values.tolist()
        )

def main():
    df = get_schools_list()
    save_to_db(df)

if __name__ == "__main__":
    main()