"""
5 LLMs ko wahi data summary + wahi 3 sawal bhejo, jawab CSV mein save karo.
Colab:  !python llm_compare.py
Output: data/clean/llm_facts.csv     (jo numbers LLMs ko diye gaye: asli, code se nikale hue)
        data/clean/llm_insights.csv  (har LLM ka har sawal ka jawab, time, status)
Jis provider ki key nahi hoti, wo skip hota hai aur CSV mein 'skipped_no_key' likha jata hai.
Pehle LLM ke jawab ke liye din mein 1-2 baar hi chalao (free limits).
"""
import os
import time

import pandas as pd

import llm_providers as L
from common import now_utc

CLEAN = "data/clean"

QUESTIONS = {
    "Q1_trends": "Is data se EV market ke 4 sab se zaroori trends bullets mein batao. Har bullet mein data ka ek number zaroor do.",
    "Q2_anomaly": "Is data mein kaun si cheez shak wali ya ghalat lagti hai (outlier, mismatch)? Sirf wahi batao jo data mein nazar aa raha hai.",
    "Q3_pakistan": "Pakistan ke EV bazar ke liye is data se 3 mukhtasir nateeje nikalo. Jo data mein nahi hai us par andaza mat lagao, saaf likho 'data mein nahi'.",
}


def facts():
    """Asli numbers pandas se nikalo (LLM se nahi). Papers mein accuracy check isi se hogi."""
    f = []
    o = pd.read_csv(f"{CLEAN}/owid_ev_sales.csv")
    last = int(o["year"].max())
    top = o[o["year"] == last].nlargest(5, "ev_sales")
    f.append(("owid_latest_year", f"Latest year in global EV sales data: {last}"))
    reg = pd.read_csv(f"{CLEAN}/owid_ev_sales_regions.csv")
    wl = reg[(reg["country"] == "World") & (reg["year"] == last)]
    if not wl.empty:
        f.append(("world_total", f"World EV sales in {last}: {int(wl['ev_sales'].iloc[0]):,}"))
    f.append(("owid_top5", f"Top 5 countries by EV sales in {last}: " +
              ", ".join(f"{r.country} {int(r.ev_sales):,}" for r in top.itertuples())))
    prev = o[o["year"] == last - 1].set_index("country")["ev_sales"]
    cn = o[(o["year"] == last) & (o["country"] == "China")]
    if not cn.empty and "China" in prev.index and prev["China"]:
        g = (cn["ev_sales"].iloc[0] / prev["China"] - 1) * 100
        f.append(("china_growth", f"China EV sales growth {last - 1}->{last}: {g:.1f}%"))

    n = pd.read_csv(f"{CLEAN}/nrel_stations_by_state.csv")
    tot = n[n["region"] == "US total"]["ev_stations"].iloc[0]
    st = n[n["region"] != "US total"].nlargest(3, "ev_stations")
    f.append(("us_stations", f"US EV charging stations total: {int(tot):,}. Top states: " +
              ", ".join(f"{r.region} {int(r.ev_stations):,}" for r in st.itertuples())))

    e = pd.read_csv(f"{CLEAN}/evdb_vehicles.csv")
    f.append(("evdb_summary", f"EV Database (Europe), {len(e)} models with specs: median range "
              f"{e['range_km'].median():.0f} km, median battery {e['battery_kwh'].median():.1f} kWh, "
              f"median efficiency {e['efficiency_wh_km'].median():.0f} Wh/km"))
    best = e.nlargest(1, "range_km").iloc[0]
    f.append(("evdb_best_range", f"Longest range model: {best['name']} {best['range_km']:.0f} km"))

    p = pd.read_csv(f"{CLEAN}/pakwheels_listings.csv")
    ok = p[p["price_pkr"].notna() & (p["suspect"].fillna("") == "")]
    f.append(("pk_listings", f"PakWheels used EV listings: {len(p)} total, {len(ok)} with clean price. "
              f"Median price PKR {ok['price_pkr'].median() / 100000:.1f} lakh"))
    byb = ok.groupby("brand")["price_pkr"].median().sort_values()
    f.append(("pk_brand_price", "Median PKR lakh by brand: " +
              ", ".join(f"{b} {v / 100000:.0f}" for b, v in byb.items())))
    f.append(("pk_suspect", f"PakWheels listings flagged suspect (missing/odd price): {int((p['suspect'].fillna('') != '').sum())}"))

    s = pd.read_csv(f"{CLEAN}/stock_prices.csv").sort_values("date")
    parts = []
    for tk, g in s.groupby("ticker"):
        ch = (g["close"].iloc[-1] / g["close"].iloc[0] - 1) * 100
        parts.append(f"{tk} {ch:+.1f}%")
    f.append(("stock_change", f"EV stock change over data window ({s['date'].min()} to {s['date'].max()}): " + ", ".join(parts)))

    w = pd.read_csv(f"{CLEAN}/wiki_pageviews.csv")
    f.append(("wiki_views", f"Wikipedia 'Electric vehicle' daily views: avg {w['views'].mean():.0f}, max {w['views'].max()}"))

    h = pd.read_csv(f"{CLEAN}/news_headlines.csv")
    f.append(("news", "Recent headlines: " + " | ".join(h["title"].head(6).str.slice(0, 90))))
    return f


def main():
    fl = facts()
    pd.DataFrame(fl, columns=["fact_id", "fact"]).assign(fetched_at=now_utc()).to_csv(
        f"{CLEAN}/llm_facts.csv", index=False, encoding="utf-8")
    context = "\n".join(f"- {t}" for _, t in fl)
    rows = []
    for provider in L.MODELS:
        for qid, q in QUESTIONS.items():
            prompt = ("Neeche EV (electric vehicle) data ke asli numbers hain. Sirf inhi par jawab do, "
                      "naye numbers mat banao. Jawab chhota aur saaf rakho.\n\nDATA:\n"
                      f"{context}\n\nSAWAL: {q}")
            row = {"provider": provider, "model": L.MODELS[provider], "question_id": qid,
                   "question": q, "answer": "", "seconds": None, "status": "", "error": "",
                   "fetched_at": now_utc()}
            t0 = time.time()
            try:
                text, model = L.ask(provider, prompt)
                row.update(model=model, answer=text.strip(), status="ok",
                           seconds=round(time.time() - t0, 1))
            except Exception as e:
                msg = str(e)
                row["status"] = "skipped_no_key" if msg == "no_key" else "error"
                row["error"] = "" if msg == "no_key" else msg[:200]
            rows.append(row)
            print(f"  {provider:11} {qid:12} {row['status']}")
            time.sleep(2)
        pd.DataFrame(rows).to_csv(f"{CLEAN}/llm_insights.csv", index=False, encoding="utf-8")
    df = pd.DataFrame(rows)
    print("\n" + df.groupby("provider")["status"].agg(lambda s: ", ".join(sorted(set(s)))).to_string())
    print(f"\nSaved: {CLEAN}/llm_insights.csv ({len(df)} rows), {CLEAN}/llm_facts.csv")
    if os.getenv("DRY_RUN") == "1":
        print("DRY_RUN tha: ye nakli jawab hain.")


if __name__ == "__main__":
    main()
