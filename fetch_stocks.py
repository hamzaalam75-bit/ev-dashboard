"""
Source 5 (API): Yahoo Finance via yfinance - EV companies ke share prices.
Install: pip install yfinance
Note: yfinance unofficial hai, kabhi kabhi rate limit ya error deta hai.
"""
import pandas as pd

from common import now_utc, save

TICKERS = {
    "TSLA": "Tesla",
    "BYDDY": "BYD",
    "NIO": "NIO",
    "RIVN": "Rivian",
    "LCID": "Lucid",
}


def main():
    print("[Stocks] Yahoo Finance")
    import yfinance as yf

    frames = []
    for ticker, company in TICKERS.items():
        try:
            h = yf.Ticker(ticker).history(period="3mo")
            if h.empty:
                print(f"  {ticker}: no data")
                continue
            h = h.reset_index()
            df = pd.DataFrame({
                "date": pd.to_datetime(h["Date"]).dt.date,
                "ticker": ticker,
                "company": company,
                "close": h["Close"].round(2),
                "volume": h["Volume"],
            })
            frames.append(df)
        except Exception as e:
            print(f"  {ticker} failed: {str(e)[:80]}")
    if not frames:
        raise RuntimeError("koi bhi ticker ka data nahi aaya")
    out = pd.concat(frames, ignore_index=True)
    out["fetched_at"] = now_utc()
    save(out, "stock_prices.csv")


if __name__ == "__main__":
    main()
