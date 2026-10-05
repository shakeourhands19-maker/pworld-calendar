import json
import os
import shutil
from datetime import datetime

DATA_DIR = "data"
SITE_DIR = "site"
TODAY = datetime.now().strftime("%Y-%m-%d")

today_dir = os.path.join(DATA_DIR, TODAY)
output_dir = os.path.join(SITE_DIR, "images", "today")
os.makedirs(output_dir, exist_ok=True)

images = []

if os.path.isdir(today_dir):
    for filename in sorted(os.listdir(today_dir)):
        source = os.path.join(today_dir, filename)
        if not os.path.isfile(source):
            continue

        ext = os.path.splitext(filename)[1].lower()
        if ext not in {".jpg", ".jpeg", ".png", ".gif", ".webp"}:
            continue

        destination = os.path.join(output_dir, filename)
        shutil.copy2(source, destination)

        images.append({
            "filename": filename,
            "url": f"images/today/{filename}"
        })

payload = {
    "date": TODAY,
    "images": images
}

with open(os.path.join(SITE_DIR, "today.json"), "w", encoding="utf-8") as f:
    json.dump(payload, f, ensure_ascii=False, indent=2)

print(f"スマホ用ページを生成しました: {TODAY}")
print(f"画像: {len(images)}枚")
