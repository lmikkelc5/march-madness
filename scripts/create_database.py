from pathlib import Path
import sqlite3

# Project root
ROOT = Path(__file__).resolve().parent.parent

# Database directory
DATABASE_DIR = ROOT / "database"
DATABASE_DIR.mkdir(exist_ok=True)

# Database file
DB_FILE = DATABASE_DIR / "practice.db"

# Connect (creates the database if it doesn't exist)
connection = sqlite3.connect(DB_FILE)

cursor = connection.cursor()

print(f"Connected to: {DB_FILE}")

cursor.execute("""
    CREATE TABLE teams (
        team_id INTEGER PRIMARY KEY,
        school TEXT NOT NULL,
        slug TEXT NOT NULL UNIQUE,
        url TEXT NOT NULL
    )
""")

cursor.execute("""
    CREATE TABLE IF NOT EXISTS team_seasons (

    team_season_id INTEGER PRIMARY KEY,

    team_id INTEGER NOT NULL,

    season INTEGER NOT NULL,

    conference TEXT,

    overall_wins INTEGER,
    overall_losses INTEGER,

    conference_wins INTEGER,
    conference_losses INTEGER,

    srs REAL,
    sos REAL,

    points_per_game REAL,
    opponent_points_per_game REAL,

    FOREIGN KEY(team_id)
        REFERENCES teams(team_id),

    UNIQUE(team_id, season)

)
""");

connection.commit()
connection.close()