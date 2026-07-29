import pandas as pd
import requests
from io import StringIO

def scrape_team_stats(url):
    URL = url
    headers = {
        "User-Agent": "Mozilla/5.0"
    }

    response = requests.get(URL, headers=headers)

    stats_df = pd.read_html(StringIO(response.text))[0]

    stats_df.columns = [
        "_".join(str(c) for c in col if "Unnamed" not in str(c)).strip("_")
        for col in stats_df.columns
    ]

    stats_df = stats_df.drop(columns=[
        "Rk",
        "Conf._W",
        "Conf._L",
        "Home_W",
        "Home_L",
        "Away_W",
        "Away_L"
    ])

    stats_df = stats_df.loc[:, stats_df.columns != ""]

    stats_df = stats_df.rename(columns={
        "Overall_G": "games",
        "Overall_W": "wins",
        "Overall_L": "losses",
        "Overall_W-L%": "win_pct",
        "Overall_SRS": "srs",
        "Overall_SOS": "sos",
        "Points_Tm.": "points_per_game",
        "Points_Opp.": "opponent_points_per_game",
        "Totals_MP": "minutes",
        "Totals_FG": "fg",
        "Totals_FGA": "fga",
        "Totals_FG%": "fg_pct",
        "Totals_3P": "three_pt",
        "Totals_3PA": "three_pt_attempts",
        "Totals_3P%": "three_pt_pct",
        "Totals_FT": "ft",
        "Totals_FTA": "fta",
        "Totals_FT%": "ft_pct",
        "Totals_ORB": "offensive_rebounds",
        "Totals_TRB": "total_rebounds",
        "Totals_AST": "assists",
        "Totals_STL": "steals",
        "Totals_BLK": "blocks",
        "Totals_TOV": "turnovers",
        "Totals_PF": "personal_fouls",
    })

    stats_df = stats_df.drop(columns=["School"])

    return stats_df