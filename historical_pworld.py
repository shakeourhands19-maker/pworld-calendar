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
MAX_RETRIES = int(os.getenv("MAX_RETRIES", "5"))

OUT = Path("historical_probe")
IMG = OUT / "images"
IMG.mkdir(parents=True, exist_ok=True)

session = requests.Session()
session.headers.update({"User-Agent": "Mozilla/5.0 (compatible; HistoricalPosterResearch/1.0)"})

def get_with_retry(url, params=None, timeout=45, attempts=MAX_RETRIES):
    last_error = None
    for attempt in range(attempts):
        try:
            response = session.get(url, params=params, timeout=timeout)
            if response.status_code in (429, 500, 502, 503, 504):
                raise requests.HTTPError(
                    f"一時的なHTTP {response.status_code}", response=response
                )
            response.raise_for_status()
            return response
        except requests.RequestException as exc:
            last_error = exc
            if attempt + 1 >= attempts:
                break
            delay = min(3 * (2 ** attempt), 30)
            print(
                f"  一時エラー: {exc}\n"
                f"  {delay}秒待って再試行します ({attempt + 2}/{attempts})",
                flush=True,
            )
            time.sleep(delay)
    raise last_error

def cdx(url):
    params = {
        "url": url,
        "output": "json",
        "filter": "statuscode:200",
        "from": START_YEAR,
        "to": END_YEAR,
        "collapse": "digest",
        "fl": "timestamp,original,mimetype,statuscode,digest",
        "limit": 500,
    }
    response = get_with_retry(CDX_URL, params=params, timeout=60)
    rows = response.json()
    return [dict(zip(rows[0], row)) for row in rows[1:]] if rows else []

def archive_url(ts, url):
    return f"https://web.archive.org/web/{ts}id_/{url}"

def original_url(src):
    if not src:
        return None
    match = re.search(
        r"https?://web\\.archive\\.org/web/\\d+(?:id_)?/(https?://.+)$", src
    )
    if match:
        return match.group(1)
    return urljoin(PAGE_URL, src)

def target(url):
    if not url:
        return False
    parsed = urlparse(url)
    return parsed.hostname == "idn.p-world.co.jp" and "img_warehouse" in parsed.path

def filename(url):
    name = Path(urlparse(url).path).name or "image.jpg"
    return re.sub(r"[^0-9A-Za-z._-]+", "_", name)

print("=" * 60)
print("P-WORLD 過去ポスター発掘テスト")
print("=" * 60)
print(f"対象期間: {START_YEAR}～{END_YEAR}")
print(f"503等の再試行: 最大{MAX_RETRIES}回")

try:
    snaps = sorted(cdx(PAGE_URL), key=lambda x: x["timestamp"], reverse=True)[:MAX_SNAPSHOTS]
except Exception as exc:
    print(f"ページ履歴一覧の取得に失敗しました: {exc}")
    print("時間を置いて再実行してください。既存カレンダーは変更していません。")
    raise

print(f"ページスナップショット: {len(snaps)}件")

records, seen = [], set()

for i, snap in enumerate(snaps, 1):
    timestamp = snap["timestamp"]
    day = f"{timestamp[:4]}-{timestamp[4:6]}-{timestamp[6:8]}"
    print(f"[{i}/{len(snaps)}] {day}", flush=True)
    try:
        response = get_with_retry(archive_url(timestamp, snap["original"]), timeout=45, attempts=3)
    except Exception as exc:
        print(f"  ページ取得失敗: {exc}", flush=True)
        time.sleep(1.5)
        continue

    soup = BeautifulSoup(response.text, "html.parser")
    page_text = soup.get_text(" ", strip=True)

    for img in soup.find_all("img"):
        src = img.get("src") or img.get("data-src") or img.get("data-original")
        url = original_url(src)
        if not target(url) or url in seen:
            continue
        seen.add(url)
        records.append({
            "capture_date": day,
            "snapshot_timestamp": timestamp,
            "original_url": url,
            "archived_url": archive_url(timestamp, url),
            "alt": img.get("alt", ""),
            "page_text_excerpt": page_text[:1000],
        })
        if len(records) >= MAX_IMAGES:
            break
    if len(records) >= MAX_IMAGES:
        break
    time.sleep(1.0)

print(f"ユニーク画像URL: {len(records)}件")
ok = failed = 0

for i, record in enumerate(records, 1):
    folder = IMG / record["capture_date"]
    folder.mkdir(parents=True, exist_ok=True)
    path = folder / f"{i:04d}_{filename(record['original_url'])}"
    try:
        response = get_with_retry(record["archived_url"], timeout=45, attempts=3)
        if not response.headers.get("content-type", "").lower().startswith("image/"):
            raise RuntimeError("画像レスポンスではありません")
        path.write_bytes(response.content)
        record["local_file"] = str(path)
        ok += 1
        print(f"  OK {i}/{len(records)}", flush=True)
    except Exception as exc:
        record["download_error"] = str(exc)
        failed += 1
        print(f"  NG {i}/{len(records)}: {exc}", flush=True)
    time.sleep(1.0)

(OUT / "index.json").write_text(
    json.dumps(records, ensure_ascii=False, indent=2), encoding="utf-8"
)
(OUT / "summary.json").write_text(
    json.dumps({
        "page_snapshots": len(snaps),
        "unique_image_urls": len(records),
        "downloaded_images": ok,
        "failed_images": failed,
        "start_year": START_YEAR,
        "end_year": END_YEAR,
        "max_retries": MAX_RETRIES,
    }, ensure_ascii=False, indent=2),
    encoding="utf-8",
)

print("=" * 60)
print(f"完了: スナップショット {len(snaps)} / 画像 {len(records)} / 成功 {ok} / 失敗 {failed}")
print("今回は既存カレンダーへ登録していません。")
