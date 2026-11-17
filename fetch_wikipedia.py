"""
Source 3 (API) : Wikimedia pageviews - "Electric vehicle" page par roz kitne views.
Source 4 (table): Wikipedia ki list of production battery electric vehicles.
(Dono ek hi site ke hain, isliye ginti mein ye 1 website hai. Isko 2 alag
sources na ginna, warna viva mein pakde jaoge.)
"""
from datetime import datetime, timedelta, timezone
from io import StringIO

import pandas as pd
import requests

from common import HEADERS, now_utc, save

TABLE_URL = ("https://en.wikipedia.org/wiki/"
             "List_of_production_battery_electric_vehicles")


def fetch_pageviews():
    print("[Wikipedia] pageviews API")
    end = datetime.now(timezone.utc).date() - timedelta(days=1)
    start = end - timedelta(days=60)
    url = ("https://wikimedia.org/api/rest_v1/metrics/pageviews/per-article/"
           f"en.wikipedia/all-access/user/Electric_vehicle/daily/"
           f"{start:%Y%m%d}/{end:%Y%m%d}")
    r = requests.get(url, headers=HEADERS, timeout=30)
    r.raise_for_status()
    df = pd.DataFrame(r.json()["items"])[["timestamp", "views"]]
    df["date"] = pd.to_datetime(df["timestamp"], format="%Y%m%d%H").dt.date
    df = df[["date", "views"]]
    df["fetched_at"] = now_utc()
    save(df, "wiki_pageviews.csv")


def fetch_models_table():
    print("[Wikipedia] EV models table")
    r = requests.get(TABLE_URL, headers=HEADERS, timeout=30)
    r.raise_for_status()
    tables = pd.read_html(StringIO(r.text))
    df = max(tables, key=len).copy()          # sabse bada table
    df.columns = [str(c).strip() for c in df.columns]
    df = df.drop(columns=[c for c in df.columns if c.lower() == "source"],
                 errors="ignore")
    for c in df.columns:                       # [1], [2] jaise footnotes hatao
        df[c] = df[c].astype(str).str.replace(r"\[.*?\]", "", regex=True).str.strip()
    df["fetched_at"] = now_utc()
    save(df, "wiki_ev_models.csv")


def main():
    for fn in (fetch_pageviews, fetch_models_table):
        try:
            fn()
        except Exception as e:
            print(f"  FAILED {fn.__name__}: {str(e)[:120]}")


if __name__ == "__main__":
    main()
