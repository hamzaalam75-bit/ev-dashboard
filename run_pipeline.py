"""
Poori pipeline ek jagah: fetch/scrape -> clean -> 5 LLM -> Excel.
GitHub Actions isi ko chalata hai:  python run_pipeline.py
Repo ki root se chalao (saari scripts root mein hain, data/ bhi root mein banta hai). Ek step fail ho to baaki chalte rehte hain.
"""
import importlib
import sys
import traceback


FETCH = ["fetch_nrel", "fetch_owid", "fetch_wikipedia", "fetch_stocks",
         "scrape_evdatabase", "scrape_news", "scrape_pakwheels"]
AFTER = ["clean_data", "llm_compare", "make_excel"]


def run(name, results):
    try:
        importlib.import_module(name).main()
        results[name] = "OK"
    except BaseException as e:               # SystemExit bhi pakro
        results[name] = f"FAILED: {str(e)[:100]}"
        traceback.print_exc()
    print()


def main():
    results = {}
    for n in FETCH + AFTER:
        run(n, results)
    print("=" * 50)
    for n, r in results.items():
        print(f"{n:22} {r}")
    print("=" * 50)
    if any(r != "OK" for k, r in results.items() if k in ("clean_data", "make_excel")):
        sys.exit(1)      # clean/excel toote to run laal ho


if __name__ == "__main__":
    main()
