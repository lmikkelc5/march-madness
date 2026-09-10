import argparse

from scripts.create_database import create_database, delete_database
from config import DB_FILE


def main():
    parser = argparse.ArgumentParser(
        description="Delete and recreate the database schema from scratch. "
        "Destructive - run only for first-time setup or after a schema change."
    )
    parser.parse_args()

    delete_database(DB_FILE)
    create_database(DB_FILE)


if __name__ == "__main__":
    main()
