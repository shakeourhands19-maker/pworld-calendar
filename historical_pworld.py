import json
import os
import re
import time
from pathlib import Path
from urllib.parse import urljoin, urlparse

import requests
from bs4 import BeautifulSoup

PAGE_URL = "https://www.p-world.co.jp/hokkaido/playland-happy-t.htm"
CDX_URL = "https://web.archive.org/cdx/search/cdx"
START_YEAR = os.getenv("START_YEAR", "2024")
END_YEAR = os.getenv("END_YEAR", "2026")
MAX_SNAPSHOTS = int(os.getenv("MAX_SNAPSHOTS", "300"))
MAX_IMAGES = int(os.getenv("MAX_IMAGES", "500"))

OUT = Path("historical_probe")
IMG = OUT / "images"
IMG.mkdir(parents=True, exist_ok=True)

s = requests.Session()
s.headers.update({"User-Agent": "Mozilla/5.0 Chrome/154.0 Safari/537.36"})

def cdx(url):
    p = {"url": url, "output": "json", "filter": "statuscode:200",
         "from": START_YEAR, "to": END_YEAR, "collapse": "digest",
         "fl": "timestamp,original,mimetype,statuscode,digest", "limit": 1000}
    r = s.get(CDX_URL, params=p, timeout=60)
    r.raise_for_status()
    rows = r.json()
    return [dict(zip(rows[0], x)) for x in rows[1:]] if rows else []

def archive_url(ts, url):
    return f"https://web.archive.org/web/{ts}id_/{url}"

def original_url(src):
    if not src:
        return None
    m = re.search(r"https?://web\.archive\.org/web/\d+(?:id_)?/(https?://.+)$", src)
    if m:
        return m.group(1)
    return urljoin(PAGE_URL, src)

def target(url):
    if not url:
        return False
    p = urlparse(url)
    return p.hostname == "idn.p-world.co.jp" and "img_warehouse" in p.path

def filename(url):
    n = Path(urlparse(url).path).name or "image.jpg"
    return re.sub(r"[^0-9A-Za-z._-]+", "_", n)

print("=" * 60)
print("P-WORLD 過去ポスター発掘テスト")
print("=" * 60)
print(f"対象期間: {START_YEAR}～{END_YEAR}")

snaps = sorted(cdx(PAGE_URL), key=lambda x: x["timestamp"], reverse=True)[:MAX_SNAPSHOTS]
print(f"ページスナップショット: {len(snaps)}件")

records, seen = [], set()

for i, snap in enumerate(snaps, 1):
    ts = snap["timestamp"]
    day = f"{ts[:4]}-{ts[4:6]}-{ts[6:8]}"
    print(f"[{i}/{len(snaps)}] {day}")
    try:
        r = s.get(archive_url(ts, snap["original"]), timeout=60)
        r.raise_for_status()
    except Exception as e:
        print(f"  ページ取得失敗: {e}")
        continue

    soup = BeautifulSoup(r.text, "html.parser")
    text = soup.get_text(" ", strip=True)

    for img in soup.find_all("img"):
        u = original_url(img.get("src") or img.get("data-src") or img.get("data-original"))
        if not target(u) or u in seen:
            continue
        seen.add(u)
        records.append({
            "capture_date": day,
            "snapshot_timestamp": ts,
            "original_url": u,
            "archived_url": archive_url(ts, u),
            "alt": img.get("alt", ""),
            "page_text_excerpt": text[:1000],
        })
        if len(records) >= MAX_IMAGES:
            break
    if len(records) >= MAX_IMAGES:
        break
    time.sleep(0.2)

print(f"ユニーク画像URL: {len(records)}件")
ok = fail = 0

for i, rec in enumerate(records, 1):
    d = IMG / rec["capture_date"]
    d.mkdir(parents=True, exist_ok=True)
    path = d / f"{i:04d}_{filename(rec['original_url'])}"
    try:
        r = s.get(rec["archived_url"], timeout=60)
        r.raise_for_status()
        if not r.headers.get("content-type", "").startswith("image/"):
            raise RuntimeError("画像レスポンスではありません")
        path.write_bytes(r.content)
        rec["local_file"] = str(path)
        ok += 1
        print(f"  OK {i}/{len(records)}")
    except Exception as e:
        rec["download_error"] = str(e)
        fail += 1
        print(f"  NG {i}/{len(records)}: {e}")
    time.sleep(0.15)

with open(OUT / "index.json", "w", encoding="utf-8") as f:
    json.dump(records, f, ensure_ascii=False, indent=2)
with open(OUT / "summary.json", "w", encoding="utf-8") as f:
    json.dump({"page_snapshots": len(snaps), "unique_image_urls": len(records),
               "downloaded_images": ok, "failed_images": fail},
              f, ensure_ascii=False, indent=2)

print("=" * 60)
print(f"完了: スナップショット {len(snaps)} / 画像 {len(records)} / 成功 {ok} / 失敗 {fail}")
print("今回は既存カレンダーへ登録していません。")
