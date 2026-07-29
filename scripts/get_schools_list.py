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

def save_to_db(df, table_name, conflict_columns):
    if isinstance(conflict_columns, str):
        conflict_columns = [conflict_columns]

    ROOT = Path(__file__).resolve().parent.parent
    DB_FILE = ROOT / "database" / "march_madness.db"

    columns = list(df.columns)

    quoted_columns = ", ".join(f'"{col}"' for col in columns)
    placeholders = ", ".join(["?"] * len(columns))
    conflict_string = ", ".join(f'"{col}"' for col in conflict_columns)

    update_string = ", ".join(
        f'"{col}" = excluded."{col}"'
        for col in columns
        if col not in conflict_columns
    )

    query = f"""
    INSERT INTO "{table_name}" ({quoted_columns})
    VALUES ({placeholders})
    ON CONFLICT({conflict_string})
    DO UPDATE SET
        {update_string};
    """

    with sqlite3.connect(DB_FILE) as connection:
        print(query)
        connection.executemany(query, df.values.tolist())
        connection.commit()
        
def main():
    pass

if __name__ == "__main__":
    main()