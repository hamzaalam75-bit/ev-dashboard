"""
EV Market Live Dashboard (Streamlit).
Data GitHub repo se padhta hai (data/clean/*.csv), jo GitHub Actions har 12 ghante update karta hai.
Chalane ka tareeqa (local):  streamlit run app.py
"""
import pandas as pd
import streamlit as st

OWNER, REPO, BRANCH = "hamzaalam75-bit", "ev-dashboard", "main"
BASE = f"https://raw.githubusercontent.com/{OWNER}/{REPO}/{BRANCH}/data/clean/"

st.set_page_config(page_title="EV Market Dashboard", layout="wide")


@st.cache_data(ttl=1800)          # 30 minute baad dobara GitHub se padhega
def load(name):
    try:
        return pd.read_csv(BASE + name)
    except Exception:
        return pd.DataFrame()


def need(df, name):
    if df.empty:
        st.warning(f"{name} load nahi hui (GitHub par data/clean/{name} check karo).")
        return False
    return True


st.title("Electric Vehicle (EV) Market Dashboard")
owid = load("owid_ev_sales.csv")
regions = load("owid_ev_sales_regions.csv")
nrel = load("nrel_stations_by_state.csv")
evdb = load("evdb_vehicles.csv")
pk = load("pakwheels_listings.csv")
stocks = load("stock_prices.csv")
wiki = load("wiki_pageviews.csv")
news = load("news_headlines.csv")
llm = load("llm_insights.csv")
facts = load("llm_facts.csv")

stamp = None
for d in (owid, nrel, evdb, pk, llm):
    if not d.empty and "fetched_at" in d.columns:
        stamp = max(stamp or "", str(d["fetched_at"].max()))
if stamp:
    st.caption(f"Data last updated (UTC): {stamp}. Auto-update every 12 hours via GitHub Actions.")

t1, t2, t3, t4, t5, t6 = st.tabs(
    ["Global Sales", "Charging (USA)", "Vehicle Specs (Europe)", "Pakistan Market",
     "Stocks & Interest", "LLM Comparison"])

with t1:
    if need(owid, "owid_ev_sales.csv"):
        last = int(owid["year"].max())
        c1, c2, c3 = st.columns(3)
        if not regions.empty:
            w = regions[(regions["country"] == "World") & (regions["year"] == last)]
            if not w.empty:
                c1.metric(f"World EV sales {last}", f"{int(w['ev_sales'].iloc[0]):,}")
        c2.metric("Countries in data", owid["country"].nunique())
        c3.metric("Latest year", last)
        yr = st.slider("Year", int(owid["year"].min()), last, last)
        top = owid[owid["year"] == yr].nlargest(10, "ev_sales").set_index("country")["ev_sales"]
        st.subheader(f"Top 10 countries by EV sales, {yr}")
        st.bar_chart(top)
        pick = st.multiselect("Compare countries over time", sorted(owid["country"].unique()),
                              default=[c for c in ["China", "United States", "Germany"] if c in set(owid["country"])])
        if pick:
            piv = owid[owid["country"].isin(pick)].pivot(index="year", columns="country", values="ev_sales")
            st.line_chart(piv)

with t2:
    if need(nrel, "nrel_stations_by_state.csv"):
        st.metric("US EV charging stations",
                  f"{int(nrel.loc[nrel['region'] == 'US total', 'ev_stations'].iloc[0]):,}"
                  if (nrel["region"] == "US total").any() else "n/a")
        st.subheader("Stations by state")
        st.bar_chart(nrel[nrel["region"] != "US total"].set_index("region")["ev_stations"])

with t3:
    if need(evdb, "evdb_vehicles.csv"):
        brands = st.multiselect("Brand", sorted(evdb["brand"].dropna().unique()))
        d = evdb[evdb["brand"].isin(brands)] if brands else evdb
        c1, c2, c3 = st.columns(3)
        c1.metric("Models", len(d))
        c2.metric("Median range (km)", f"{d['range_km'].median():.0f}")
        c3.metric("Median battery (kWh)", f"{d['battery_kwh'].median():.1f}")
        st.subheader("Battery size vs range")
        st.scatter_chart(d, x="battery_kwh", y="range_km")
        st.subheader("Average range by brand (brands with 5+ models)")
        g = d.groupby("brand")["range_km"].agg(["mean", "count"])
        st.bar_chart(g[g["count"] >= 5]["mean"].sort_values(ascending=False).head(15))
        st.dataframe(d[["name", "brand", "range_km", "battery_kwh", "efficiency_wh_km", "est_price_eur"]],
                     use_container_width=True)
        st.caption("est_price_eur is an estimate (price per km of range x range), not a real price.")

with t4:
    if need(pk, "pakwheels_listings.csv"):
        ok = pk[pk["price_pkr"].notna() & (pk["suspect"].fillna("") == "")]
        c1, c2, c3 = st.columns(3)
        c1.metric("Listings", len(pk))
        c2.metric("With clean price", len(ok))
        c3.metric("Median price (lakh PKR)", f"{ok['price_pkr'].median() / 1e5:.1f}" if len(ok) else "n/a")
        st.subheader("Median price by brand (lakh PKR)")
        st.bar_chart(ok.groupby("brand")["price_pkr_lakh"].median().sort_values())
        st.subheader("Listings by city")
        st.bar_chart(pk["city"].value_counts().head(10))
        show_sus = st.checkbox("Show suspect listings only")
        st.dataframe(pk[pk["suspect"].fillna("") != ""] if show_sus else pk, use_container_width=True)

with t5:
    if need(stocks, "stock_prices.csv"):
        st.subheader("EV company share prices (close)")
        stocks["date"] = pd.to_datetime(stocks["date"])
        st.line_chart(stocks.pivot_table(index="date", columns="ticker", values="close"))
    if need(wiki, "wiki_pageviews.csv"):
        st.subheader("Wikipedia 'Electric vehicle' daily views")
        wiki["date"] = pd.to_datetime(wiki["date"])
        st.line_chart(wiki.set_index("date")["views"])
    if need(news, "news_headlines.csv"):
        st.subheader("Latest headlines")
        st.dataframe(news[[c for c in ["site", "title", "url"] if c in news.columns]].head(30),
                     use_container_width=True)

with t6:
    if need(llm, "llm_insights.csv"):
        st.write("The same data summary and the same 3 questions were sent to 5 LLMs.")
        q = st.selectbox("Question", llm["question"].unique())
        d = llm[llm["question"] == q]
        for r in d.itertuples():
            with st.expander(f"{r.provider}  ({r.model})  status: {r.status}"):
                st.write(r.answer)
        st.subheader("Average response time (seconds)")
        st.bar_chart(llm[llm["status"] == "ok"].groupby("provider")["seconds"].mean())
        if need(facts, "llm_facts.csv"):
            with st.expander("Facts given to the LLMs (computed by code)"):
                st.dataframe(facts[["fact_id", "fact"]], use_container_width=True)
