"""
Source (scraping): EV Database (ev-database.org)   -- v2
Fix: pehle regex galat number utha raha tha. Ab har cheez uske label se parho:
"Range 720 km", "Battery 108.7 kWh", "Efficiency 151 Wh/km" waghera.
Kuch entries ("Discontinued ..." wali, ~428) mein specs hoti hi nahi, unmein range/price khali rahegi.
"""
import re
from urllib.parse import urljoin

import pandas as pd
import requests
from bs4 import BeautifulSoup

from common import now_utc, save

URL = "https://ev-database.org/"
UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/120 Safari/537.36")


def to_num(s):
    if s is None:
        return None
    s = s.replace(",", "")
    try:
        return float(s)
    except ValueError:
        return None


def clean_name(text):
    """'BMW i3 50 xDrive (MY27) BMW i3 50 xDrive' -> 'BMW i3 50 xDrive (MY27)'"""
    w = text.split()
    for k in range(1, len(w)):
        if " ".join(w[k:]) in " ".join(w[:k]):
            return " ".join(w[:k])
    return text


def find_container(h):
    node = h
    for _ in range(6):
        node = node.parent
        if node is None:
            break
        t = node.get_text(" ", strip=True)
        if ("km" in t or "kWh" in t) and len(t) < 2500:
            return node
    return h.parent


def grab(pattern, text):
    m = re.search(pattern, text)
    return to_num(m.group(1)) if m else None


def parse_text(text):
    price_m = re.search(r"Price[^€£\d]{0,40}([€£])\s*([\d.,]+)", text)
    price = None
    if price_m:
        price = to_num(re.sub(r"[.,]", "", price_m.group(2)))   # 88.990 / 88,990 -> 88990
    return {
        "range_km": grab(r"(?<!Stop )Range\*?\s+(\d{2,4})\s*km", text),
        "efficiency_wh_km": grab(r"Efficiency\*?\s+(\d{2,4})\s*Wh/km", text),
        "battery_kwh": grab(r"Battery\*?\s+(\d{1,3}(?:\.\d+)?)\s*kWh", text),
        "fastcharge_kw": grab(r"Fastcharge\*?\s+(\d{2,4})\s*kW", text),
        "acceleration_0_100_s": grab(r"0-100\s+(\d{1,2}(?:\.\d+)?)\s*sec", text),
        "weight_kg": grab(r"Weight\s+([\d,]{3,6})\s*kg", text),
        "cargo_l": grab(r"Cargo Vol\.\s+([\d,]{2,5})\s*L", text),
        "price": price,
        "currency": price_m.group(1) if price_m else None,
        "price_raw": price_m.group(0)[:60] if price_m else None,
    }


def parse(html):
    try:
        soup = BeautifulSoup(html, "lxml")
    except Exception:
        soup = BeautifulSoup(html, "html.parser")
    rows, seen = [], set()
    for h in soup.find_all("h2"):
        a = h.find("a") or h.find_parent("a")
        if not a or not a.get("href"):
            continue
        link = urljoin(URL, a["href"])
        if link in seen:
            continue
        seen.add(link)
        text = find_container(h).get_text(" ", strip=True)
        row = {"name": clean_name(h.get_text(" ", strip=True))[:120], "url": link}
        row.update(parse_text(text))
        row["has_specs"] = row["range_km"] is not None
        row["raw_text"] = text[:1500]
        rows.append(row)
    return rows


def main():
    print("[EV Database] scraping")
    r = requests.get(URL, headers={"User-Agent": UA}, timeout=60)
    r.raise_for_status()
    rows = parse(r.text)
    if not rows:
        raise RuntimeError("koi vehicle nahi mila, site ka layout badal gaya?")
    df = pd.DataFrame(rows)
    df["fetched_at"] = now_utc()
    print(f"  vehicles: {len(df)} | specs wali: {int(df['has_specs'].sum())} | "
          f"price mili: {df['price'].notna().sum()}")
    cols = ["name", "range_km", "battery_kwh", "efficiency_wh_km", "price", "currency"]
    print(df[df["has_specs"]][cols].head(6).to_string())
    print("\n  PRICE CHECK (ye 3 lines mujhe paste karo):")
    for t in df[df["price"].notna()]["price_raw"].head(3):
        print("   ", t)
    save(df, "evdb_vehicles.csv")


if __name__ == "__main__":
    main()
