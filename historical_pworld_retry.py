import json
import os
import re
import time
from pathlib import Path
from urllib.parse import urlparse

import requests

INPUT = Path("historical_probe/index.json")
OUT = Path("historical_probe_retry")
IMG = OUT / "images"
IMG.mkdir(parents=True, exist_ok=True)

CDX = "https://web.archive.org/cdx/search/cdx"
START_YEAR = os.getenv("START_YEAR", "2024")
END_YEAR = os.getenv("END_YEAR", "2026")
MAX_IMAGES = int(os.getenv("MAX_IMAGES", "100"))
MAX_CANDIDATES = int(os.getenv("MAX_CANDIDATES", "5"))
MAX_RETRIES = int(os.getenv("MAX_RETRIES", "5"))

session = requests.Session()
session.headers.update({"User-Agent": "Mozilla/5.0 (compatible; HistoricalPosterResearch/1.0)"})

def request_with_retry(url, *, params=None, timeout=30, attempts=MAX_RETRIES):
    last_error = None
    for attempt in range(attempts):
        try:
            response = session.get(url, params=params, timeout=timeout)
            if response.status_code in (429, 500, 502, 503, 504):
                raise requests.HTTPError(f"temporary HTTP {response.status_code}", response=response)
            response.raise_for_status()
            return response
        except (requests.RequestException, requests.Timeout) as exc:
            last_error = exc
            if attempt + 1 >= attempts:
                break
            delay = min(2 ** attempt, 20)
            print(f"    一時エラー、{delay}秒後に再試行 ({attempt + 2}/{attempts}): {exc}", flush=True)
            time.sleep(delay)
    raise last_error

def cdx(url):
    params = {
        "url": url,
        "output": "json",
        "filter": "statuscode:200",
        "from": START_YEAR,
        "to": END_YEAR,
        "fl": "timestamp,original,mimetype,statuscode,digest",
        "collapse": "digest",
        "limit": 50,
    }
    response = request_with_retry(CDX, params=params, timeout=45)
    rows = response.json()
    return [dict(zip(rows[0], row)) for row in rows[1:]] if rows else []

def archive_url(timestamp, url):
    return f"https://web.archive.org/web/{timestamp}id_/{url}"

def clean(url):
    # P-WORLD appends a numeric cache-busting query. Search both forms below.
    return re.sub(r"\\?\\d+$", "", url or "")

def filename(index, url):
    name = Path(urlparse(url).path).name or "image.jpg"
    return f"{index:04d}_{re.sub(r'[^0-9A-Za-z._-]+', '_', name)}"

records = json.loads(INPUT.read_text(encoding="utf-8"))
records = records[:MAX_IMAGES]

ok = failed = cdx_failed = 0
print("=" * 60)
print(f"画像URL個別再発掘テスト: {len(records)}枚")
print(f"候補確認: 最大{MAX_CANDIDATES}件/URL")
print(f"一時エラー再試行: 最大{MAX_RETRIES}回")
print("=" * 60)

for index, record in enumerate(records, 1):
    original = record.get("original_url", "")
    cleaned = clean(original)
    print(f"[{index}/{len(records)}] {cleaned}", flush=True)

    # Query付きURLとクエリなしURLの両方を調べ、重複候補をまとめる。
    variants = list(dict.fromkeys([original, cleaned]))
    candidates = []
    seen_timestamps = set()
    had_cdx_success = False

    for variant in variants:
        try:
            found = cdx(variant)
            had_cdx_success = True
            for cap in found:
                timestamp = cap.get("timestamp", "")
                if timestamp and timestamp not in seen_timestamps:
                    seen_timestamps.add(timestamp)
                    candidates.append((cap, variant))
        except Exception as exc:
            print(f"  CDX検索失敗 ({'query付き' if variant == original and original != cleaned else '通常URL'}): {exc}", flush=True)
        time.sleep(1.5)

    candidates.sort(key=lambda item: item[0].get("timestamp", ""), reverse=True)
    candidates = candidates[:MAX_CANDIDATES]
    print(f"  保存候補: {len(candidates)}件", flush=True)

    if not had_cdx_success:
        record["retry_error"] = "CDX検索がすべて失敗"
        cdx_failed += 1

    recovered = False
    for cap, variant in candidates:
        timestamp = cap["timestamp"]
        try:
            response = request_with_retry(archive_url(timestamp, variant), timeout=30, attempts=3)
            content_type = response.headers.get("content-type", "").lower()
            if not content_type.startswith("image/"):
                print(f"    候補 {timestamp}: 画像ではないためスキップ", flush=True)
                continue
            path = IMG / filename(index, variant)
            path.write_bytes(response.content)
            record.update({
                "clean_original_url": cleaned,
                "recovered_timestamp": timestamp,
                "recovered_url": archive_url(timestamp, variant),
                "local_file": str(path),
                "recovered_size": len(response.content),
                "recovered_content_type": content_type,
            })
            record.pop("recovery_failed", None)
            ok += 1
            recovered = True
            print(f"  OK: {timestamp} / {len(response.content):,} bytes", flush=True)
            break
        except Exception as exc:
            print(f"    候補 {timestamp} 取得失敗: {exc}", flush=True)
        time.sleep(1)

    if not recovered:
        record["recovery_failed"] = True
        failed += 1
        print("  NG", flush=True)

    # Waybackへの連続アクセスを抑え、503を起こしにくくする。
    time.sleep(2)

(OUT / "index.json").write_text(
    json.dumps(records, ensure_ascii=False, indent=2), encoding="utf-8"
)
(OUT / "summary.json").write_text(
    json.dumps({
        "input_images": len(records),
        "recovered": ok,
        "failed": failed,
        "cdx_all_failed": cdx_failed,
        "start_year": START_YEAR,
        "end_year": END_YEAR,
        "max_candidates": MAX_CANDIDATES,
        "max_retries": MAX_RETRIES,
    }, ensure_ascii=False, indent=2),
    encoding="utf-8",
)

print("=" * 60)
print(f"完了: {len(records)}件中 {ok}件取得 / {failed}件失敗")
print(f"CDX全滅: {cdx_failed}件")
