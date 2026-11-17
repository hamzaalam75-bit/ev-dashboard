"""
Debug helper: jab koi scraper 0 rows de, to ye page ka structure dikhata hai.
Colab:  !python inspect_page.py https://www.pakwheels.com/used-cars/search/-/ft_electric/
Output paste karo.
"""
import sys
from collections import Counter

import requests
from bs4 import BeautifulSoup

UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/120 Safari/537.36")


def main():
    if len(sys.argv) < 2:
        print("use: python inspect_page.py <url>")
        return
    url = sys.argv[1]
    r = requests.get(url, headers={"User-Agent": UA}, timeout=30)
    print("status:", r.status_code, "| size KB:", len(r.content) // 1024,
          "| final url:", r.url)
    soup = BeautifulSoup(r.text, "html.parser")
    print("title:", soup.title.get_text(strip=True)[:100] if soup.title else None)
    low = r.text.lower()
    print("block words:", [w for w in ["captcha", "just a moment", "access denied",
                                       "verify you are human", "cf-chl"] if w in low])
    print("top classes:", Counter(c for t in soup.find_all(True)
                                  for c in t.get("class", [])).most_common(15))
    for h in soup.find_all(["h2", "h3"])[:5]:
        print("heading:", h.get_text(" ", strip=True)[:80], "| parent class:",
              h.parent.get("class"))
    links = [a["href"] for a in soup.find_all("a", href=True)][:10]
    print("first links:", links)


if __name__ == "__main__":
    main()
