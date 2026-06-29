from scripts.get_schools_list import get_schools_list, save_to_db
from scripts.create_database import create_database, delete_database
from config import DB_FILE

def main():
    #create database and tables
    delete_database(DB_FILE)
    create_database(DB_FILE)

    # create schools list and load to table
    url = "https://www.sports-reference.com/cbb/seasons/men/2026-school-stats.html"
    schools = get_schools_list(url)
    save_to_db(schools, "teams", "slug")

    # Seasons
    # seasons = get_team_seasons(...)
    # save_to_db(seasons, "team_seasons", ("team_id", "season"))

    # Games
    # games = get_games(...)
    # save_to_db(games, "games", "game_id")

    # Players
    # players = get_players(...)
    # save_to_db(players, "players", "player_id")



if __name__ == "__main__":
    main()