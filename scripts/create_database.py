from pathlib import Path
import sqlite3
import os
from config import DB_FILE

def delete_database(DB_FILE):
    if DB_FILE.exists():
        os.remove(DB_FILE)

def create_database(DB_FILE):
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
        CREATE TABLE coaches (
            coach_id INTEGER PRIMARY KEY,
            name TEXT NOT NULL,
            slug TEXT NOT NULL UNIQUE,
            url TEXT
        )
    """)

    cursor.execute("""
        CREATE TABLE conferences (
            conference_id INTEGER PRIMARY KEY,
            name TEXT NOT NULL,
            slug TEXT NOT NULL UNIQUE
        )
    """)

    cursor.execute("""
        CREATE TABLE players (
            player_id INTEGER PRIMARY KEY,
            name TEXT NOT NULL,
            slug TEXT NOT NULL UNIQUE,
            url TEXT
        )
    """)

    cursor.execute("""
        CREATE TABLE seasons (
            season INTEGER PRIMARY KEY,

            champion_team_id INTEGER,
            runner_up_team_id INTEGER,

            num_tournament_teams INTEGER,
            selection_sunday_date TEXT,
            notes TEXT,

            FOREIGN KEY(champion_team_id) REFERENCES teams(team_id),
            FOREIGN KEY(runner_up_team_id) REFERENCES teams(team_id)
        )
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS team_seasons (

    team_season_id INTEGER PRIMARY KEY,

    team_id INTEGER NOT NULL,
    season INTEGER NOT NULL,
    coach_id INTEGER,

    games INTEGER,
    wins INTEGER,
    losses INTEGER,
    win_pct REAL,

    srs REAL,
    sos REAL,

    points INTEGER,
    opponent_points INTEGER,

    minutes INTEGER,

    fg INTEGER,
    fga INTEGER,
    fg_pct REAL,

    three_pt INTEGER,
    three_pt_attempts INTEGER,
    three_pt_pct REAL,

    ft INTEGER,
    fta INTEGER,
    ft_pct REAL,

    offensive_rebounds INTEGER,
    total_rebounds INTEGER,

    assists INTEGER,
    steals INTEGER,
    blocks INTEGER,
    turnovers INTEGER,
    personal_fouls INTEGER,

    FOREIGN KEY(team_id)
        REFERENCES teams(team_id),
    FOREIGN KEY(coach_id)
        REFERENCES coaches(coach_id),

    UNIQUE(team_id, season)

)
""")

    cursor.execute("""
        CREATE TABLE team_conferences (
            team_conference_id INTEGER PRIMARY KEY,

            team_id INTEGER NOT NULL,
            conference_id INTEGER NOT NULL,
            season INTEGER NOT NULL,

            FOREIGN KEY(team_id) REFERENCES teams(team_id),
            FOREIGN KEY(conference_id) REFERENCES conferences(conference_id),

            UNIQUE(team_id, season)
        )
    """)

    cursor.execute("""
        CREATE TABLE player_seasons (
            player_season_id INTEGER PRIMARY KEY,

            player_id INTEGER NOT NULL,
            team_id INTEGER NOT NULL,
            season INTEGER NOT NULL,

            class TEXT,
            position TEXT,

            games_played INTEGER,
            games_started INTEGER,
            minutes INTEGER,

            points INTEGER,
            total_rebounds INTEGER,
            assists INTEGER,
            steals INTEGER,
            blocks INTEGER,
            turnovers INTEGER,
            personal_fouls INTEGER,

            fg INTEGER,
            fga INTEGER,
            fg_pct REAL,

            three_pt INTEGER,
            three_pt_attempts INTEGER,
            three_pt_pct REAL,

            ft INTEGER,
            fta INTEGER,
            ft_pct REAL,

            FOREIGN KEY(player_id) REFERENCES players(player_id),
            FOREIGN KEY(team_id) REFERENCES teams(team_id),

            UNIQUE(player_id, season)
        )
    """)

    cursor.execute("""
        CREATE TABLE injuries (
            injury_id INTEGER PRIMARY KEY,

            player_id INTEGER NOT NULL,
            season INTEGER NOT NULL,

            start_date TEXT,
            end_date TEXT,
            description TEXT,

            FOREIGN KEY(player_id) REFERENCES players(player_id)
        )
    """)

    cursor.execute("""
        CREATE TABLE games (
            game_id INTEGER PRIMARY KEY,

            boxscore_slug TEXT UNIQUE,

            season INTEGER NOT NULL,
            date TEXT NOT NULL,

            home_team_id INTEGER,
            away_team_id INTEGER,
            home_score INTEGER,
            away_score INTEGER,

            is_neutral_site INTEGER NOT NULL DEFAULT 0,
            overtimes INTEGER NOT NULL DEFAULT 0,
            is_conference_game INTEGER NOT NULL DEFAULT 0,
            is_tournament_game INTEGER NOT NULL DEFAULT 0,

            round TEXT,
            region TEXT,

            FOREIGN KEY(home_team_id) REFERENCES teams(team_id),
            FOREIGN KEY(away_team_id) REFERENCES teams(team_id)
        )
    """)

    cursor.execute("""
        CREATE TABLE team_game_stats (
            team_game_stat_id INTEGER PRIMARY KEY,

            game_id INTEGER NOT NULL,
            team_id INTEGER NOT NULL,
            opponent_id INTEGER NOT NULL,

            points INTEGER,

            fg INTEGER,
            fga INTEGER,
            fg_pct REAL,

            three_pt INTEGER,
            three_pt_attempts INTEGER,
            three_pt_pct REAL,

            ft INTEGER,
            fta INTEGER,
            ft_pct REAL,

            offensive_rebounds INTEGER,
            total_rebounds INTEGER,

            assists INTEGER,
            steals INTEGER,
            blocks INTEGER,
            turnovers INTEGER,
            personal_fouls INTEGER,

            FOREIGN KEY(game_id) REFERENCES games(game_id),
            FOREIGN KEY(team_id) REFERENCES teams(team_id),
            FOREIGN KEY(opponent_id) REFERENCES teams(team_id),

            UNIQUE(game_id, team_id)
        )
    """)

    cursor.execute("""
        CREATE TABLE rankings (
            ranking_id INTEGER PRIMARY KEY,

            team_id INTEGER NOT NULL,
            season INTEGER NOT NULL,
            poll_date TEXT NOT NULL,
            poll_type TEXT NOT NULL,
            rank INTEGER,

            FOREIGN KEY(team_id) REFERENCES teams(team_id),

            UNIQUE(team_id, season, poll_date, poll_type)
        )
    """)

    cursor.execute("""
        CREATE TABLE tournament_seeds (
            tournament_seed_id INTEGER PRIMARY KEY,

            team_id INTEGER NOT NULL,
            season INTEGER NOT NULL,

            seed INTEGER,
            region TEXT,
            overall_seed INTEGER,

            FOREIGN KEY(team_id) REFERENCES teams(team_id),

            UNIQUE(team_id, season)
        )
    """)

    connection.commit()
    connection.close()
