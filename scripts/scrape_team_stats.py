import pandas as pd
import requests
from io import StringIO

URL = "https://www.sports-reference.com/cbb/schools/michigan/men/2026.html"

headers = {
    "User-Agent": "Mozilla/5.0"
}

response = requests.get(URL, headers=headers)

print(response.status_code)

tables = pd.read_html(StringIO(response.text))

print(f"Found {len(tables)} tables")

for i, table in enumerate(tables):
    print("=" * 60)
    print(f"TABLE {i}")
    print("=" * 60)

    print(table.head())

    print()