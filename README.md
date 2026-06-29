# My attempt at predicting future march madness tournaments using past data. 

## create_database.py

Code that creates my schema for my database. 

### TEAMS table

team_id - Unique ID
school - Name of the school
slug - Lowercase and spaceless version for creating URLS
url - The whole URL for the team

### team_seasons

team_season_id - Unique ID for each team's season
team_id - References the corresponding team in the `teams` table
season - The season year (e.g. 2026)
conference - Conference the team competed in that season
overall_wins - Total number of wins during the season
overall_losses - Total number of losses during the season
conference_wins - Wins against conference opponents
conference_losses - Losses against conference opponents
srs - Simple Rating System; overall team strength accounting for scoring margin and strength of schedule
sos - Strength of Schedule; average difficulty of the team's opponents
points_per_game - Average points scored per game
opponent_points_per_game - Average points allowed per game