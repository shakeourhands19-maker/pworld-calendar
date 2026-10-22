import json
import re
import time
from datetime import date, timedelta
from pathlib import Path

import requests
from bs4 import BeautifulSoup

STORE_URL = "https://horulog.com/hall/%E5%8C%97%E6%B5%B7%E9%81%93/%E3%83%97%E3%83%AC%E3%82%A4%E3%83%A9%E3%83%B3%E3%83%89%E3%83%8F%E3%83%83%E3%83%94%E3%83%BC%E6%89%8B%E7%A8%B2%E5%89%8D%E7%94%B0%E5%BA%97"
OUT_DIR = Path("site/horulog_data")
START_DATE = date(2026, 10, 14)
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/130.0 Safari/537.36",
    "Accept-Language": "ja,en-US;q=0.9,en;q=0.8",
}

def scrape_day(session, day):
    url = f"{STORE_URL}/{day.isoformat()}"
    response = session.get(url, timeout=30)
    if response.status_code != 200:
        print(f"{day}: HTTP {response.status_code}")
        return None
    soup = BeautifulSoup(response.text, "html.parser")
    mapping = {}
    for table in soup.find_all("table"):
        rows = table.find_all("tr")
        for row in rows:
            cells = row.find_all(["td", "th"], recursive=False)
            if len(cells) < 2:
                continue
            number = cells[0].get_text(" ", strip=True).replace(",", "")
            machine = cells[1].get_text(" ", strip=True)
            if re.fullmatch(r"\d{3,4}", number) and machine and machine != "機種":
                mapping[number] = machine
    # Guard against pages with an error or an unexpected table.
    if len(mapping) < 100:
        print(f"{day}: mapping incomplete ({len(mapping)} rows); skip")
        return None
    return {
        "date": day.isoformat(),
        "source": url,
        "count": len(mapping),
        "machines": mapping,
    }

def main():
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    today = date.today()
    session = requests.Session()
    session.headers.update(HEADERS)
    updated = 0
    # Historical dates are collected as well, so selecting a past date in the island editor
    # uses the machine lineup for that date rather than today's lineup.
    day = START_DATE
    last_day = today - timedelta(days=1)
    while day <= last_day:
        path = OUT_DIR / f"{day.isoformat()}.json"
        # Re-fetch recent days to allow late corrections; retain older successful snapshots.
        if path.exists() and day < today - timedelta(days=10):
            day += timedelta(days=1)
            continue
        try:
            result = scrape_day(session, day)
            if result:
                path.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
                updated += 1
                print(f"{day}: saved {result['count']} machine mappings")
        except Exception as exc:
            print(f"{day}: {type(exc).__name__}: {exc}")
        time.sleep(0.5)
        day += timedelta(days=1)
    print(f"Horulog collection finished; updated {updated} date files.")

if __name__ == "__main__":
    main()
