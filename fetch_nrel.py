"""
Source 1 (API): NREL/NLR Alternative Fuels Data Center
US ke states mein EV charging stations ki ginti.

v2: 429 (Too Many Requests) aaye to ruk kar dobara koshish karta hai.
DEMO_KEY ki limit kam hai. Behtar: developer.nlr.gov se free key lo, phir
    Colab mein:  import os; os.environ["NREL_API_KEY"] = "teri_key"
"""
import os
import time

import pandas as pd
import requests

from common import HEADERS, now_utc, save

API_KEY = os.getenv("NREL_API_KEY", "DEMO_KEY")
BASE = "https://developer.nlr.gov/api/alt-fuel-stations/v1.json"
STATES = ["CA", "TX", "FL", "NY", "WA", "IL", "GA", "NC", "CO", "MA"]
RETRIES = 4
WAIT_ON_429 = 20   # seconds


def get_total(extra=None):
    params = {"api_key": API_KEY, "fuel_type": "ELEC", "limit": 1}
    if extra:
        params.update(extra)
    for attempt in range(1, RETRIES + 1):
        r = requests.get(BASE, params=params, headers=HEADERS, timeout=30)
        if r.status_code == 429:
            print(f"    429, {WAIT_ON_429}s ruk raha hoon (koshish {attempt}/{RETRIES})")
            time.sleep(WAIT_ON_429)
            continue
        r.raise_for_status()
        return r.json().get("total_results")
    raise RuntimeError("429 baar baar aaya, free API key lo")


def main():
    print("[NREL] EV charging stations")
    stamp = now_utc()
    rows, failed = [], []
    for region, extra in [("US total", None)] + [(s, {"state": s}) for s in STATES]:
        try:
            rows.append({"region": region, "ev_stations": get_total(extra),
                         "fetched_at": stamp})
        except Exception as e:
            failed.append(region)
            print(f"  {region} failed: {str(e)[:80]}")
        time.sleep(3)
    save(pd.DataFrame(rows), "nrel_stations_by_state.csv")
    if failed:
        # run_all ko "OK" ke bajaye sahi status dikhane ke liye
        raise RuntimeError(f"partial data, ye regions missing: {failed}")


if __name__ == "__main__":
    main()
