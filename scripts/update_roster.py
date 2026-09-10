import argparse
import traceback

from scripts.checkpoint import is_done, mark_done
from scripts.get_schools_list import get_schools_list, save_to_db
from scripts.scrape_team_stats import scrape_and_save_team_seasons
from scripts.scrape_conferences import scrape_conferences_and_memberships
from config import DB_FILE

JOB_NAME = "roster"


def scrape_teams(season, db_file):
    url = f"https://www.sports-reference.com/cbb/seasons/men/{season}-school-stats.html"
    teams_df = get_schools_list(url)
    save_to_db(teams_df, "teams", "slug", db_file)


STEPS = {
    "teams": scrape_teams,
    "team_seasons": lambda season, db_file: scrape_and_save_team_seasons(season, db_file),
    "conferences": lambda season, db_file: scrape_conferences_and_memberships(season, db_file),
}


def run(start_season, end_season, db_file=DB_FILE, force=False):
    failures = []

    for season in range(start_season, end_season + 1):
        for step_name, step_fn in STEPS.items():
            key = f"{season}:{step_name}"

            if not force and is_done(JOB_NAME, key):
                print(f"Skipping {key} (already done)")
                continue

            print(f"Running {key}...")
            try:
                step_fn(season, db_file)
                mark_done(JOB_NAME, key)
            except Exception:
                print(f"FAILED {key}")
                traceback.print_exc()
                failures.append(key)

    if failures:
        print(f"\n{len(failures)} step(s) failed, rerun this script to retry them:")
        for key in failures:
            print(f"  {key}")
    else:
        print("\nAll roster steps completed.")


def main():
    parser = argparse.ArgumentParser(
        description="Backfill teams, team_seasons, and conferences across a season range. "
        "Safe to rerun - completed (season, step) pairs are skipped unless --force is passed."
    )
    parser.add_argument("--start-season", type=int, required=True)
    parser.add_argument("--end-season", type=int, required=True)
    parser.add_argument("--force", action="store_true", help="Redo steps even if already marked done")
    args = parser.parse_args()

    run(args.start_season, args.end_season, force=args.force)


if __name__ == "__main__":
    main()
