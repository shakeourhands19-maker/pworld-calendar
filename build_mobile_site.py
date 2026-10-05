import json
import os
import shutil
from datetime import datetime

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

print(f"スマホ用ページを生成しました: {TODAY}")
print(f"履歴日数: {len(dates)}")
print(f"レイアウト数: {len(layouts)}")
