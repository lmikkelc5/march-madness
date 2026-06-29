import pandas as pd
import requests
from io import StringIO

URL = "https://www.sports-reference.com/cbb/seasons/men/2026-school-stats.html"

headers = {
    "User-Agent": "Mozilla/5.0"
}

response = requests.get(URL, headers=headers)

stats_df = pd.read_html(StringIO(response.text))[0]

stats_df.columns = [
    "_".join(str(c) for c in col if "Unnamed" not in str(c)).strip("_")
    for col in stats_df.columns
]

print(stats_df.head())