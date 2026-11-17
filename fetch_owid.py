"""
Source 2 (API/CSV): Our World in Data - electric car sales by country and year.
"""
from io import StringIO

import pandas as pd
import requests

from common import HEADERS, now_utc, save

URL = "https://ourworldindata.org/grapher/electric-car-sales.csv"


def main():
    print("[OWID] electric car sales")
    r = requests.get(URL, headers=HEADERS, timeout=60)
    r.raise_for_status()
    df = pd.read_csv(StringIO(r.text))
    print("  columns:", list(df.columns))
    df["fetched_at"] = now_utc()
    save(df, "owid_ev_sales.csv")


if __name__ == "__main__":
    main()
