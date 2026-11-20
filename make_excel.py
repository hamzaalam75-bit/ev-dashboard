"""
data/clean/ ki saari CSV files ko ek hi Excel file (har CSV ek sheet) mein jama karta hai.
Power BI mein ek hi baar "Get data > Excel" se saari tables load ho jati hain.
Colab:  !python make_excel.py        (phir ev_dashboard_data.xlsx download karo)
"""
import glob
import os

import pandas as pd

CLEAN = "data/clean"
OUT = "ev_dashboard_data.xlsx"
DROP_COLS = {"raw_text"}          # lambi text columns Power BI ko bhaari kar deti hain


def main():
    files = sorted(glob.glob(os.path.join(CLEAN, "*.csv")))
    if not files:
        raise SystemExit("data/clean/ mein koi CSV nahi mili: pehle clean_data.py chalao")
    with pd.ExcelWriter(OUT, engine="openpyxl") as xw:
        for f in files:
            name = os.path.splitext(os.path.basename(f))[0][:31]      # Excel sheet naam max 31 chars
            df = pd.read_csv(f)
            df = df.drop(columns=[c for c in df.columns if c in DROP_COLS])
            for c in df.columns:
                if c == "date":
                    df[c] = pd.to_datetime(df[c], errors="coerce")
            df.to_excel(xw, sheet_name=name, index=False)
            print(f"  {name:32} {len(df):5} rows")
    print(f"\nSaved: {OUT} ({os.path.getsize(OUT) // 1024} KB)")


if __name__ == "__main__":
    main()
