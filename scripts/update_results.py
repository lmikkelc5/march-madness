import argparse
import traceback

from scripts.checkpoint import is_done, mark_done
from scripts.scrape_games import build_games_for_season, build_team_game_stats_for_season
from scripts.scrape_tournament import assign_tournament_rounds, scrape_and_save_tournament_seeds
from config import DB_FILE

JOB_NAME = "results"

STEPS = {
    "games": build_games_for_season,
    "team_game_stats": build_team_game_stats_for_season,
    "tournament_seeds": scrape_and_save_tournament_seeds,
    "tournament_rounds": assign_tournament_rounds,
}


def run(start_season, end_season, db_file=DB_FILE, force=False, steps=None):
    failures = []
    steps_to_run = {name: STEPS[name] for name in steps} if steps else STEPS

    for season in range(start_season, end_season + 1):
        for step_name, step_fn in steps_to_run.items():
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
        print("\nAll results steps completed.")


def main():
    parser = argparse.ArgumentParser(
        description="Backfill games, team_game_stats, tournament_seeds, and tournament_rounds across a season range. "
        "Requires update_roster.py to have already populated that season's teams/team_seasons/team_conferences. "
        "team_game_stats is expensive (one request per game) and checkpoints per-game internally, "
        "so an interrupted run resumes without refetching completed games."
    )
    parser.add_argument("--start-season", type=int, required=True)
    parser.add_argument("--end-season", type=int, required=True)
    parser.add_argument("--force", action="store_true", help="Redo steps even if already marked done")
    parser.add_argument(
        "--steps", type=lambda s: s.split(","), default=None,
        help=f"Comma-separated subset of steps to run ({', '.join(STEPS)}). Defaults to all.",
    )
    args = parser.parse_args()

    run(args.start_season, args.end_season, force=args.force, steps=args.steps)


if __name__ == "__main__":
    main()
