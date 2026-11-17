"""
Sources 6, 7, 8 (scraping): Electrek, InsideEVs, CleanTechnica
Homepage ki headlines + links. Ye 3 alag websites hain, har ek ki apni robots.txt check hoti hai.
"""
import time
from urllib.parse import urljoin, urlparse
from urllib.robotparser import RobotFileParser

import pandas as pd
import requests
from bs4 import BeautifulSoup

from common import now_utc, save

UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/120 Safari/537.36")
H = {"User-Agent": UA}
SITES = {
    "Electrek": "https://electrek.co/",
    "InsideEVs": "https://insideevs.com/",
    "CleanTechnica": "https://cleantechnica.com/",
}


def robots_ok(url):
    p = urlparse(url)
    try:
        r = requests.get(f"{p.scheme}://{p.netloc}/robots.txt", headers=H, timeout=15)
        if r.status_code != 200:
            return True
        rp = RobotFileParser()
        rp.parse(r.text.splitlines())
        return rp.can_fetch("*", url)
    except Exception:
        return True


def scrape(site, url):
    if not robots_ok(url):
        raise RuntimeError("robots.txt allow nahi karta")
    r = requests.get(url, headers=H, timeout=30)
    r.raise_for_status()
    soup = BeautifulSoup(r.text, "html.parser")
    rows, seen = [], set()
    for h in soup.find_all(["h2", "h3"]):
        title = h.get_text(" ", strip=True)
        a = h.find("a") or h.find_parent("a")
        if len(title) < 20 or not a or not a.get("href"):
            continue
        link = urljoin(url, a["href"])
        if link in seen:
            continue
        seen.add(link)
        rows.append({"site": site, "title": title, "url": link})
    return rows


def main():
    print("[News] Electrek, InsideEVs, CleanTechnica")
    all_rows, failed = [], []
    for site, url in SITES.items():
        try:
            rows = scrape(site, url)
            print(f"  {site}: {len(rows)} headlines")
            if not rows:
                failed.append(site)
            all_rows += rows
        except Exception as e:
            failed.append(site)
            print(f"  {site} FAILED: {str(e)[:100]}")
        time.sleep(2)
    if not all_rows:
        raise RuntimeError("kisi bhi site se headlines nahi mili")
    df = pd.DataFrame(all_rows)
    df["fetched_at"] = now_utc()
    save(df, "news_headlines.csv")
    if failed:
        raise RuntimeError(f"partial data, ye sites fail: {failed}")


if __name__ == "__main__":
    main()
