"""Shared helpers. Har script isi se headers aur save function leti hai."""
import os
from datetime import datetime, timezone

HEADERS = {
    "User-Agent": "ev-dashboard-student-project/1.0 (university project; "
                  "contact: student)"
}
DATA_DIR = "data"


def now_utc():
    return datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")


def save(df, filename):
    os.makedirs(DATA_DIR, exist_ok=True)
    path = os.path.join(DATA_DIR, filename)
    df.to_csv(path, index=False, encoding="utf-8")
    print(f"  saved {path}  ({len(df)} rows, {len(df.columns)} cols)")
    return path
