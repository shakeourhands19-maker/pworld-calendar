import json
import os
import shutil
import subprocess
from datetime import datetime

from PIL import Image

DATA_DIR = "data"
SITE_DIR = "site"
TODAY = datetime.now().strftime("%Y-%m-%d")
IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".gif", ".webp"}

os.makedirs(SITE_DIR, exist_ok=True)
os.makedirs(os.path.join(SITE_DIR, "images"), exist_ok=True)
os.makedirs(os.path.join(SITE_DIR, "layouts"), exist_ok=True)

dates = []
for date in sorted(os.listdir(DATA_DIR), reverse=True):
    date_dir = os.path.join(DATA_DIR, date)
    if not os.path.isdir(date_dir) or date == "layouts":
        continue
    if len(date) != 10 or date[4] != "-" or date[7] != "-":
        continue

    site_date_dir = os.path.join(SITE_DIR, "images", date)
    os.makedirs(site_date_dir, exist_ok=True)
    images = []

    for filename in sorted(os.listdir(date_dir)):
        source = os.path.join(date_dir, filename)
        if not os.path.isfile(source):
            continue
        if os.path.splitext(filename)[1].lower() not in IMAGE_EXTENSIONS:
            continue
        shutil.copy2(source, os.path.join(site_date_dir, filename))
        images.append({"filename": filename, "url": f"images/{date}/{filename}"})

    if images:
        dates.append({"date": date, "images": images})

# ============================================================
# index.json の手動登録画像もスマホ用サイトへ取り込む
# 画像が data/日付/ファイル名 にない場合は data/直下を参照する
# ============================================================

index_path = os.path.join(DATA_DIR, "index.json")
if os.path.isfile(index_path):
    with open(index_path, "r", encoding="utf-8") as f:
        date_index = json.load(f)

    date_map = {item["date"]: item for item in dates}
    for date, filenames in date_index.items():
        if not isinstance(filenames, list):
            continue

        item = date_map.get(date)
        if item is None:
            item = {"date": date, "images": []}
            dates.append(item)
            date_map[date] = item

        site_date_dir = os.path.join(SITE_DIR, "images", date)
        os.makedirs(site_date_dir, exist_ok=True)

        for filename in filenames:
            if not isinstance(filename, str):
                continue
            if any(img["filename"] == filename for img in item["images"]):
                continue

            dated_source = os.path.join(DATA_DIR, date, filename)
            root_source = os.path.join(DATA_DIR, filename)
            source = dated_source if os.path.isfile(dated_source) else root_source
            if not os.path.isfile(source):
                print(f"index.json の画像が見つかりません: {date}/{filename}")
                continue

            shutil.copy2(source, os.path.join(site_date_dir, filename))
            item["images"].append({
                "filename": filename,
                "url": f"images/{date}/{filename}"
            })

    dates.sort(key=lambda x: x["date"], reverse=True)

today_images = next((x["images"] for x in dates if x["date"] == TODAY), [])
with open(os.path.join(SITE_DIR, "today.json"), "w", encoding="utf-8") as f:
    json.dump({"date": TODAY, "images": today_images}, f, ensure_ascii=False, indent=2)

with open(os.path.join(SITE_DIR, "dates.json"), "w", encoding="utf-8") as f:
    json.dump(dates, f, ensure_ascii=False, indent=2)

layout_index = {}
layout_path = os.path.join(DATA_DIR, "layout_index.json")
if os.path.isfile(layout_path):
    with open(layout_path, "r", encoding="utf-8") as f:
        layout_index = json.load(f)

layout_dir = os.path.join(DATA_DIR, "layouts")
if os.path.isdir(layout_dir):
    for filename in os.listdir(layout_dir):
        source = os.path.join(layout_dir, filename)
        if os.path.isfile(source):
            shutil.copy2(source, os.path.join(SITE_DIR, "layouts", filename))

layouts = []
for layout_id, info in sorted(layout_index.items()):
    images = info.get("images", [])
    if not images:
        continue
    first = images[0]
    representative = f"images/{first['date']}/{first['filename']}" if isinstance(first, dict) else f"layouts/{layout_id}.jpg"
    layouts.append({
        "id": layout_id,
        "count": len(images),
        "representative": representative,
        "images": [
            {"date": x["date"], "filename": x["filename"], "url": f"images/{x['date']}/{x['filename']}"}
            for x in images if isinstance(x, dict) and x.get("date") and x.get("filename")
        ]
    })

with open(os.path.join(SITE_DIR, "layouts.json"), "w", encoding="utf-8") as f:
    json.dump(layouts, f, ensure_ascii=False, indent=2)

shutil.copy2(layout_path, os.path.join(SITE_DIR, "layout_index.json")) if os.path.isfile(layout_path) else None

# ============================================================
# OCR検索用インデックス
# ============================================================

ocr_path = os.path.join(DATA_DIR, "ocr_index.json")
ocr_index = {}

if os.path.isfile(ocr_path):
    try:
        with open(ocr_path, "r", encoding="utf-8") as f:
            ocr_index = json.load(f)
    except Exception:
        ocr_index = {}

for item in dates:
    date = item["date"]
    for image in item["images"]:
        filename = image["filename"]
        key = f"{date}/{filename}"
        if key in ocr_index:
            continue

        source = os.path.join(DATA_DIR, date, filename)
        if not os.path.isfile(source):
            continue

        try:
            result = subprocess.run(
                [
                    "tesseract",
                    source,
                    "stdout",
                    "-l",
                    "jpn+eng",
                    "--psm",
                    "6",
                ],
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="ignore",
                timeout=30,
            )
            ocr_index[key] = {
                "date": date,
                "filename": filename,
                "url": image["url"],
                "text": result.stdout or "",
            }
        except Exception as e:
            print(f"OCR失敗: {key} / {e}")

with open(ocr_path, "w", encoding="utf-8") as f:
    json.dump(ocr_index, f, ensure_ascii=False, indent=2)

with open(os.path.join(SITE_DIR, "ocr_index.json"), "w", encoding="utf-8") as f:
    json.dump(ocr_index, f, ensure_ascii=False, indent=2)

print(f"OCR検索インデックス: {len(ocr_index)}件")

print(f"スマホ用ページを生成しました: {TODAY}")
print(f"履歴日数: {len(dates)}")
print(f"レイアウト数: {len(layouts)}")
