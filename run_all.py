"""
Sab fetch scripts ek ke baad ek chalata hai.
Ek fail ho to baaki chalte rehte hain. Aakhir mein summary deta hai.
Colab:  !pip install yfinance lxml
        !python run_all.py
"""
import importlib
import traceback

MODULES = ["fetch_nrel", "fetch_owid", "fetch_wikipedia", "fetch_stocks"]


def main():
    results = {}
    for name in MODULES:
        try:
            importlib.import_module(name).main()
            results[name] = "OK"
        except Exception as e:
            results[name] = f"FAILED: {str(e)[:100]}"
            traceback.print_exc()
        print()
    print("=" * 40)
    for name, res in results.items():
        print(f"{name:18} {res}")
    print("=" * 40)
    print("Ye summary aur koi error ho to poora paste karo.")


if __name__ == "__main__":
    main()
