"""
Source (scraping): PakWheels - Pakistan mein electric gaariyon ki listings   -- v3
Fix: har page par 12 "featured" ads (Civic, Swift...) aati thin jo electric nahi hain.
     Asli listings ke title mein "for Sale" hota hai, featured ads ke mein nahi: bas wahi rakho.
Naye columns: price_pkr (number), city (link se), mileage_km.
"""
import re
import time
from urllib.parse import urljoin

import pandas as pd
import requests
from bs4 import BeautifulSoup

from common import now_utc, save

UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/120 Safari/537.36")
H = {"User-Agent": UA}
BASE_URL = "https://www.pakwheels.com/used-cars/electric/389926"
MAX_PAGES = 3
LISTING_HREF = re.compile(r"/used-cars/[^?#]*-\d{5,}")


def price_to_pkr(text):
    """'27.45 lacs' -> 2745000 | '1.11 crore' -> 11100000 | '4,750,000' -> 4750000"""
    if not text:
        return None
    m = re.match(r"([\d.,]+)\s*(lacs?|lakh|crore)?", text.strip(), re.I)
    if not m:
        return None
    try:
        n = float(m.group(1).replace(",", ""))
    except ValueError:
        return None
    unit = (m.group(2) or "").lower()
    if unit.startswith(("lac", "lakh")):
        n *= 100_000
    elif unit == "crore":
        n *= 10_000_000
    return int(round(n))


def city_from_url(link):
    m = re.search(r"for-sale-in-(.+)-\d{5,}$", link)
    return m.group(1).replace("-", " ").title() if m else None


def parse(html, base):
    soup = BeautifulSoup(html, "html.parser")
    rows, seen = [], set()
    for a in soup.find_all("a", href=True):
        href = a["href"]
        title = a.get_text(" ", strip=True)
        if not LISTING_HREF.search(href) or "for sale" not in title.lower():
            continue                                  # featured ads aur "Sell Your Car" yahan hat jate hain
        link = urljoin(base, href).split("?")[0]
        if link in seen:
            continue
        seen.add(link)
        box = a                                       # sirf is listing ka apna card lo, padosi listing nahi
        for _ in range(8):
            parent = box.parent
            if parent is None:
                break
            others = {urljoin(base, x["href"]).split("?")[0]
                      for x in parent.find_all("a", href=True)
                      if LISTING_HREF.search(x["href"])}
            if len(others - {link}) > 0:              # parent mein doosri listing bhi hai, yahin ruk jao
                break
            box = parent
        text = box.get_text(" ", strip=True)
        price = re.search(r"PKR\s*([\d.,]+\s*(?:lacs?|lakh|crore)?)", text, re.I)
        price_text = price.group(1).strip() if price else None
        year = re.search(r"\b(19|20)\d{2}\b", title)
        km = re.search(r"([\d,]{3,7})\s*km", text, re.I)
        rows.append({
            "title": re.sub(r"\s+", " ", title)[:120],
            "url": link,
            "price_text": price_text,
            "price_pkr": price_to_pkr(price_text),
            "city": city_from_url(link),
            "year": int(year.group(0)) if year else None,
            "mileage_km": int(km.group(1).replace(",", "")) if km else None,
            "raw_text": text[:300],
        })
    return rows


def main():
    print("[PakWheels] electric listings")
    all_rows, seen = [], set()
    for page in range(1, MAX_PAGES + 1):
        url = BASE_URL if page == 1 else f"{BASE_URL}?page={page}"
        r = requests.get(url, headers=H, timeout=30)
        print(f"  page {page} -> {r.status_code}")
        if r.status_code != 200:
            break
        new = [x for x in parse(r.text, url) if x["url"] not in seen]
        print(f"    asli listings: {len(new)}")
        if not new:
            break
        seen.update(x["url"] for x in new)
        all_rows += new
        time.sleep(2)
    if not all_rows:
        raise RuntimeError("koi listing nahi mili: inspect_page.py chalao aur output paste karo")
    df = pd.DataFrame(all_rows)
    df["fetched_at"] = now_utc()
    print(f"  total: {len(df)} | price wali: {df['price_pkr'].notna().sum()} | "
          f"mileage wali: {df['mileage_km'].notna().sum()}")
    print(df[["title", "price_pkr", "city", "year", "mileage_km"]].to_string())
    save(df, "pakwheels_listings.csv")


if __name__ == "__main__":
    main()
