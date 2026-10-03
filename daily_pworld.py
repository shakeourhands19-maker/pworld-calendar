import os
import re
import shutil
import subprocess
from datetime import datetime
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup
from PIL import Image, ImageEnhance, ImageFilter


# =========================================================
# 設定
# =========================================================

PAGE_URL = "https://www.p-world.co.jp/hokkaido/playland-happy-t.htm"

TESSERACT = r"D:\tesseract OCR\tesseract.exe"

IMAGE_DIR = "downloaded_images"
DATA_DIR = "data"

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/154.0.0.0 Safari/537.36"
    ),
    "Referer": "https://www.google.com/"
}

# 開店画像として判定
KEYWORDS = ["開店", "OPEN"]

# 開店画像でも除外する文字
EXCLUDE_KEYWORDS = [
    "抽選開始",
    "抽選への参加"
]


# =========================================================
# フォルダ準備
# =========================================================

os.makedirs(IMAGE_DIR, exist_ok=True)
os.makedirs(DATA_DIR, exist_ok=True)


# =========================================================
# P-WORLDページ取得
# =========================================================

print("P-WORLDページを取得しています...")

response = requests.get(
    PAGE_URL,
    headers=HEADERS,
    timeout=30
)

response.raise_for_status()

soup = BeautifulSoup(response.text, "html.parser")

print("ページ取得成功")
print()


# =========================================================
# P-WORLDの告知画像URLを取得
# =========================================================

image_urls = []

for img in soup.find_all("img"):

    src = img.get("src")

    if not src:
        continue

    image_url = urljoin(PAGE_URL, src)

    # P-WORLDの告知画像だけ
    if "img_warehouse" not in image_url:
        continue

    if image_url not in image_urls:
        image_urls.append(image_url)


print(f"告知画像を {len(image_urls)} 枚発見しました。")
print()


# =========================================================
# 今日の日付
# =========================================================

today = datetime.now().strftime("%Y-%m-%d")

today_dir = os.path.join(DATA_DIR, today)

os.makedirs(today_dir, exist_ok=True)

print(f"保存先: {today_dir}")
print()


# =========================================================
# 画像取得 → OCR → 判定
# =========================================================

found = []

for index, image_url in enumerate(image_urls, 1):

    # 拡張子判定
    if ".png" in image_url.lower():
        ext = ".png"
    else:
        ext = ".jpg"

    filename = f"{index:02d}{ext}"

    downloaded_file = os.path.join(
        IMAGE_DIR,
        filename
    )

    temp_file = os.path.join(
        IMAGE_DIR,
        "_ocr_temp.png"
    )

    print(
        f"[{index}/{len(image_urls)}] {filename}",
        end=" "
    )

    try:

        # -------------------------------------------------
        # 画像ダウンロード
        # -------------------------------------------------

        r = requests.get(
            image_url,
            headers=HEADERS,
            timeout=30
        )

        r.raise_for_status()

        with open(downloaded_file, "wb") as f:
            f.write(r.content)


        # -------------------------------------------------
        # OCR用画像作成
        # -------------------------------------------------

        img = Image.open(downloaded_file).convert("L")

        # 3倍拡大
        img = img.resize(
            (
                img.width * 3,
                img.height * 3
            )
        )

        # コントラスト強化
        img = ImageEnhance.Contrast(img).enhance(2.0)

        # シャープ化
        img = img.filter(ImageFilter.SHARPEN)

        img.save(temp_file)


        # -------------------------------------------------
        # OCR
        # -------------------------------------------------

        result = subprocess.run(
            [
                TESSERACT,
                temp_file,
                "stdout",
                "-l",
                "jpn+eng",
                "--psm",
                "6"
            ],
            capture_output=True,
            text=True,
            encoding="utf-8",
            timeout=15
        )

        text = result.stdout


        # -------------------------------------------------
        # 除外判定
        # -------------------------------------------------

        excluded = []

        for keyword in EXCLUDE_KEYWORDS:

            if keyword in text:
                excluded.append(keyword)

        if excluded:

            print(
                f"→ 除外（{', '.join(excluded)}）"
            )

            continue


        # -------------------------------------------------
        # 開店判定
        # -------------------------------------------------

        matched = []

        for keyword in KEYWORDS:

            if keyword.lower() in text.lower():
                matched.append(keyword)


        if matched:

            print(
                f"★ 開店画像 "
                f"（{', '.join(matched)}）"
            )

            # 開店画像として保存
            destination = os.path.join(
                today_dir,
                filename
            )

            shutil.copy2(
                downloaded_file,
                destination
            )

            found.append(filename)

        else:

            print("→ 該当なし")


    except subprocess.TimeoutExpired:

        print("→ OCRタイムアウト")


    except Exception as e:

        print(f"→ エラー: {e}")


    finally:

        # OCR一時ファイル削除
        if os.path.exists(temp_file):

            os.remove(temp_file)


# =========================================================
# 結果
# =========================================================

print()
print("=" * 60)
print("本日の判定結果")
print("=" * 60)

if found:

    for filename in found:

        print(
            f"★ {filename}"
        )

else:

    print(
        "開店画像は見つかりませんでした。"
    )


print()
print(f"保存先: {today_dir}")
print()
print("完了しました！")