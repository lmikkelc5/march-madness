from bs4 import BeautifulSoup
import pandas as pd
import sqlite3

from scripts.http_utils import polite_get
from config import DB_FILE

def get_schools_list(URL):
    response = polite_get(URL)

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

    return df

def save_to_db(df, table_name, conflict_columns, db_file=DB_FILE):
    if isinstance(conflict_columns, str):
        conflict_columns = [conflict_columns]

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

    with sqlite3.connect(db_file) as connection:
        connection.executemany(query, df.values.tolist())
        connection.commit()
        
def main():
    pass

if __name__ == "__main__":
    main()