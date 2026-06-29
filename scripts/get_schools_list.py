from bs4 import BeautifulSoup
import pandas as pd
import requests
from pathlib import Path
import sqlite3

def get_schools_list(URL):
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

def save_to_db(df, table_name, conflict_column):
    ROOT = Path(__file__).resolve().parent.parent
    DB_FILE = ROOT / "database" / "march_madness.db"

    columns = list(df.columns)
    column_string = ", ".join(columns)
    placeholders = ", ".join(["?"] * len(columns))

    # Update every column except the conflict column
    update_string = ", ".join(
        f"{col}=excluded.{col}"
        for col in columns
        if col != conflict_column
    )

    query = f"""
    INSERT INTO {table_name} ({column_string})
    VALUES ({placeholders})
    ON CONFLICT({conflict_column})
    DO UPDATE SET
        {update_string};
    """

    with sqlite3.connect(DB_FILE) as connection:
        connection.executemany(query, df.values.tolist())
        connection.commit()

def main():
    pass

if __name__ == "__main__":
    main()