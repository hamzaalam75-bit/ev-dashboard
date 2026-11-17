"""
Safai (cleaning): data/ ki raw CSV files -> data/clean/ mein saaf CSV files (Power BI inhi ko padhega).
Chalane ka tareeqa (Colab):   !python clean_data.py
Raw files ko haath nahi lagata. Jo cheez shak wali ho use 'suspect' column mein flag karta hai, delete nahi karta.
"""
import os
import re

import pandas as pd

RAW, OUT = "data", "data/clean"
os.makedirs(OUT, exist_ok=True)
report = []


def load(name):
    return pd.read_csv(os.path.join(RAW, name))


def write(df, name, note=""):
    df.to_csv(os.path.join(OUT, name), index=False, encoding="utf-8")
    report.append(f"{name:28} {len(df):5} rows  {note}")


def brand_of(title):
    t = str(title).strip()
    for two in ("Mercedes Benz", "Land Rover", "Alfa Romeo", "Rolls Royce"):
        if t.lower().startswith(two.lower()):
            return "Mercedes-Benz" if two == "Mercedes Benz" else two
    return t.split()[0] if t else None


def clean_owid():
    d = load("owid_ev_sales.csv")
    d = d.rename(columns={"Entity": "country", "Code": "iso_code", "Year": "year",
                          "Electric cars sold": "ev_sales"})
    d["year"] = d["year"].astype(int)
    # World, Europe, EU27, Rest of World jama (aggregate) hain: mulkon ke saath ginne se double count hota hai
    agg = d["iso_code"].isna() | d["iso_code"].astype(str).str.startswith("OWID_")
    cols = ["country", "iso_code", "year", "ev_sales", "fetched_at"]
    write(d[~agg][cols], "owid_ev_sales.csv", f"(sirf mulk; {d[agg]['country'].nunique()} aggregate alag)")
    write(d[agg][cols], "owid_ev_sales_regions.csv", "(World/Europe/EU/Rest of World)")


def clean_wiki_models():
    d = load("wiki_ev_models.csv")
    n0 = len(d)
    d = d.dropna(subset=["Model", "Manufacturer"])
    d = d[d["Model"].astype(str).str.lower() != "nan"]
    d = d.rename(columns={"Model": "model", "Calendar year produced": "year_produced",
                          "Body style": "body_style", "Manufacturer": "manufacturer",
                          "Marque origin": "origin"})
    d["year_produced"] = pd.to_numeric(d["year_produced"], errors="coerce").astype("Int64")
    write(d, "wiki_ev_models.csv", f"({n0 - len(d)} khali rows hataayi)")


def clean_wiki_views():
    d = load("wiki_pageviews.csv")
    d["date"] = pd.to_datetime(d["date"]).dt.date
    write(d, "wiki_pageviews.csv")


def clean_stocks():
    d = load("stock_prices.csv")
    d["date"] = pd.to_datetime(d["date"]).dt.date
    write(d, "stock_prices.csv", f"({d['ticker'].nunique()} companies)")


def clean_nrel():
    d = load("nrel_stations_by_state.csv")
    d = d.rename(columns={"region": "region", "ev_stations": "ev_stations"})
    write(d, "nrel_stations_by_state.csv", f"(regions: {len(d)})")


def clean_news():
    d = load("news_headlines.csv").drop_duplicates(subset=["url"])
    write(d, "news_headlines.csv", f"(sites: {d['site'].nunique()})")


def clean_evdb():
    d = load("evdb_vehicles.csv")
    d = d.rename(columns={"price": "price_per_km_range"})   # asal mein euro har km range ke
    d["brand"] = d["name"].map(brand_of)
    d["est_price_eur"] = (d["price_per_km_range"] * d["range_km"]).round(-2)  # andaza, asli price nahi
    keep = ["name", "brand", "range_km", "battery_kwh", "efficiency_wh_km", "fastcharge_kw",
            "acceleration_0_100_s", "weight_kg", "cargo_l", "price_per_km_range",
            "est_price_eur", "has_specs", "url", "fetched_at"]
    specs = d[d["has_specs"]][keep]
    write(specs, "evdb_vehicles.csv",
          f"(specs wali; {len(d) - len(specs)} bina-specs rows alag)")
    write(d[~d["has_specs"]][["name", "brand", "battery_kwh", "url", "fetched_at"]],
          "evdb_no_specs.csv", "(Discontinued/bina specs)")


def clean_pakwheels():
    d = load("pakwheels_listings.csv").drop_duplicates(subset=["url"]).copy()
    d["brand"] = d["title"].map(brand_of)
    d["model_key"] = d["title"].map(lambda t: " ".join(re.sub(r"\s+", " ", str(t)).split()[:3]))
    d["price_pkr_lakh"] = (d["price_pkr"] / 100_000).round(2)
    med = d.groupby("model_key")["price_pkr"].transform("median")
    cnt = d.groupby("model_key")["price_pkr"].transform("count")
    price_off = (cnt >= 2) & ((d["price_pkr"] < 0.3 * med) | (d["price_pkr"] > 3 * med))
    old = d["year"] < 2012
    no_price = d["price_pkr"].isna()
    d["suspect"] = ""
    d.loc[price_off, "suspect"] += "price_outlier;"
    d.loc[old, "suspect"] += "very_old_maybe_not_EV;"
    d.loc[no_price, "suspect"] += "no_price;"
    cols = [c for c in ["title", "brand", "year", "price_pkr", "price_pkr_lakh", "city",
                        "mileage_km", "suspect", "url", "fetched_at"] if c in d.columns]
    write(d[cols], "pakwheels_listings.csv", f"({(d['suspect'] != '').sum()} rows 'suspect' flag ke saath)")


def main():
    steps = [clean_owid, clean_wiki_models, clean_wiki_views, clean_stocks, clean_nrel,
             clean_news, clean_evdb, clean_pakwheels]
    for fn in steps:
        try:
            fn()
        except Exception as e:
            report.append(f"{fn.__name__:28} FAILED: {str(e)[:100]}")
    print("=" * 70)
    print("\n".join(report))
    print("=" * 70)
    print("Output data/clean/ mein hai. Ye poora summary paste karo.")


if __name__ == "__main__":
    main()
