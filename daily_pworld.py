import os
import re
import shutil
import subprocess
import json
from datetime import datetime
from zoneinfo import ZoneInfo
from urllib.parse import urljoin
@@ -41,6 +42,18 @@
]


# =========================================================
# レイアウト判定設定
# =========================================================

# 比較用画像サイズ
LAYOUT_IMAGE_SIZE = (64, 64)

# この値より小さければ「同じレイアウト」と判定
# 小さいほど厳しく、大きいほど緩くなる
LAYOUT_THRESHOLD = 18


# =========================================================
# フォルダ準備
# =========================================================
@@ -49,6 +62,121 @@
os.makedirs(DATA_DIR, exist_ok=True)


# =========================================================
# レイアウト特徴量作成
# =========================================================

def create_layout_signature(image_path):
    """
    画像を小さくしてグレースケール化し、
    明るさの平均を基準に正規化した特徴量を作る。

    日付や細かい文字の違いにはある程度強く、
    全体的なレイアウトの違いを判定しやすくする。
    """

    img = Image.open(image_path).convert("L")

    # アスペクト比を保ったまま縮小
    img.thumbnail(LAYOUT_IMAGE_SIZE)

    # 64x64のキャンバスを作る
    canvas = Image.new(
        "L",
        LAYOUT_IMAGE_SIZE,
        255
    )

    x = (
        LAYOUT_IMAGE_SIZE[0] - img.width
    ) // 2

    y = (
        LAYOUT_IMAGE_SIZE[1] - img.height
    ) // 2

    canvas.paste(
        img,
        (x, y)
    )

    # コントラストを軽く正規化
    canvas = ImageEnhance.Contrast(
        canvas
    ).enhance(1.5)

    # 0～1に変換
    pixels = list(canvas.getdata())

    average = sum(pixels) / len(pixels)

    # 平均値との差を特徴量にする
    signature = [
        (pixel - average) / 255.0
        for pixel in pixels
    ]

    return signature


# =========================================================
# レイアウト距離計算
# =========================================================

def calculate_layout_distance(
    signature1,
    signature2
):
    """
    2つの画像特徴量の平均絶対誤差を計算
    """

    if len(signature1) != len(signature2):
        return 999

    total = 0

    for a, b in zip(
        signature1,
        signature2
    ):
        total += abs(a - b)

    return (
        total / len(signature1)
    ) * 100


# =========================================================
# 既存レイアウトを読み込む
# =========================================================

layout_index_file = os.path.join(
    DATA_DIR,
    "layout_index.json"
)

if os.path.exists(layout_index_file):

    try:

        with open(
            layout_index_file,
            "r",
            encoding="utf-8"
        ) as f:

            layout_data = json.load(f)

    except Exception:

        layout_data = {}

else:

    layout_data = {}


# =========================================================
# P-WORLDページ取得
# =========================================================
@@ -63,7 +191,10 @@

response.raise_for_status()

soup = BeautifulSoup(response.text, "html.parser")
soup = BeautifulSoup(
    response.text,
    "html.parser"
)

print("ページ取得成功")
print()
@@ -82,31 +213,49 @@
    if not src:
        continue

    image_url = urljoin(PAGE_URL, src)
    image_url = urljoin(
        PAGE_URL,
        src
    )

    # P-WORLDの告知画像だけ
    if "img_warehouse" not in image_url:
        continue

    if image_url not in image_urls:
        image_urls.append(image_url)

        image_urls.append(
            image_url
        )

print(f"告知画像を {len(image_urls)} 枚発見しました。")

print(
    f"告知画像を {len(image_urls)} 枚発見しました。"
)
print()


# =========================================================
# 今日の日付
# =========================================================

today = datetime.now(ZoneInfo("Asia/Tokyo")).strftime("%Y-%m-%d")
today = datetime.now(
    ZoneInfo("Asia/Tokyo")
).strftime("%Y-%m-%d")

today_dir = os.path.join(DATA_DIR, today)
today_dir = os.path.join(
    DATA_DIR,
    today
)

os.makedirs(today_dir, exist_ok=True)
os.makedirs(
    today_dir,
    exist_ok=True
)

print(f"保存先: {today_dir}")
print(
    f"保存先: {today_dir}"
)
print()


@@ -116,15 +265,23 @@

found = []

for index, image_url in enumerate(image_urls, 1):
for index, image_url in enumerate(
    image_urls,
    1
):

    # 拡張子判定
    if ".png" in image_url.lower():

        ext = ".png"

    else:

        ext = ".jpg"

    filename = f"{index:02d}{ext}"
    filename = (
        f"{index:02d}{ext}"
    )

    downloaded_file = os.path.join(
        IMAGE_DIR,
@@ -137,7 +294,8 @@
    )

    print(
        f"[{index}/{len(image_urls)}] {filename}",
        f"[{index}/{len(image_urls)}] "
        f"{filename}",
        end=" "
    )

@@ -155,15 +313,23 @@

        r.raise_for_status()

        with open(downloaded_file, "wb") as f:
            f.write(r.content)
        with open(
            downloaded_file,
            "wb"
        ) as f:

            f.write(
                r.content
            )


        # -------------------------------------------------
        # OCR用画像作成
        # -------------------------------------------------

        img = Image.open(downloaded_file).convert("L")
        img = Image.open(
            downloaded_file
        ).convert("L")

        # 3倍拡大
        img = img.resize(
@@ -174,12 +340,18 @@
        )

        # コントラスト強化
        img = ImageEnhance.Contrast(img).enhance(2.0)
        img = ImageEnhance.Contrast(
            img
        ).enhance(2.0)

        # シャープ化
        img = img.filter(ImageFilter.SHARPEN)
        img = img.filter(
            ImageFilter.SHARPEN
        )

        img.save(temp_file)
        img.save(
            temp_file
        )


        # -------------------------------------------------
@@ -214,12 +386,17 @@
        for keyword in EXCLUDE_KEYWORDS:

            if keyword in text:
                excluded.append(keyword)

                excluded.append(
                    keyword
                )

        if excluded:

            print(
                f"→ 除外（{', '.join(excluded)}）"
                f"→ 除外（"
                f"{', '.join(excluded)}"
                f"）"
            )

            continue
@@ -234,7 +411,10 @@
        for keyword in KEYWORDS:

            if keyword.lower() in text.lower():
                matched.append(keyword)

                matched.append(
                    keyword
                )


        if matched:
@@ -255,29 +435,41 @@
                destination
            )

            found.append(filename)
            found.append(
                filename
            )

        else:

            print("→ 該当なし")
            print(
                "→ 該当なし"
            )


    except subprocess.TimeoutExpired:

        print("→ OCRタイムアウト")
        print(
            "→ OCRタイムアウト"
        )


    except Exception as e:

        print(f"→ エラー: {e}")
        print(
            f"→ エラー: {e}"
        )


    finally:

        # OCR一時ファイル削除
        if os.path.exists(temp_file):
        if os.path.exists(
            temp_file
        ):

            os.remove(temp_file)
            os.remove(
                temp_file
            )


# =========================================================
@@ -303,34 +495,62 @@
        "開店画像は見つかりませんでした。"
    )


# =========================================================
# index.jsonを作成
import json
# =========================================================

index_file = os.path.join(DATA_DIR, "index.json")
index_file = os.path.join(
    DATA_DIR,
    "index.json"
)

index_data = {}

for date_name in sorted(os.listdir(DATA_DIR)):
for date_name in sorted(
    os.listdir(DATA_DIR)
):

    date_dir = os.path.join(DATA_DIR, date_name)
    date_dir = os.path.join(
        DATA_DIR,
        date_name
    )

    if not os.path.isdir(date_dir):
    if not os.path.isdir(
        date_dir
    ):
        continue

    if not re.match(r"^\d{4}-\d{2}-\d{2}$", date_name):
    if not re.match(
        r"^\d{4}-\d{2}-\d{2}$",
        date_name
    ):
        continue

    files = []

    for filename in sorted(os.listdir(date_dir)):
    for filename in sorted(
        os.listdir(date_dir)
    ):

        if filename.lower().endswith(
            (".jpg", ".jpeg", ".png")
            (
                ".jpg",
                ".jpeg",
                ".png"
            )
        ):
            files.append(filename)

            files.append(
                filename
            )

    if files:
        index_data[date_name] = files

        index_data[
            date_name
        ] = files


with open(
    index_file,
@@ -345,9 +565,235 @@
        indent=2
    )

print("index.jsonを更新しました。")
print(
    "index.jsonを更新しました。"
)


# =========================================================
# レイアウト判定
# =========================================================

print()
print("=" * 60)
print("基本レイアウト判定")
print("=" * 60)


# ---------------------------------------------------------
# 既存画像をすべて取得
# ---------------------------------------------------------

all_images = []

for date_name in sorted(
    os.listdir(DATA_DIR)
):

    date_dir = os.path.join(
        DATA_DIR,
        date_name
    )

    if not os.path.isdir(
        date_dir
    ):
        continue

    if not re.match(
        r"^\d{4}-\d{2}-\d{2}$",
        date_name
    ):
        continue

    for filename in sorted(
        os.listdir(date_dir)
    ):

        if not filename.lower().endswith(
            (
                ".jpg",
                ".jpeg",
                ".png"
            )
        ):
            continue

        path = os.path.join(
            date_dir,
            filename
        )

        all_images.append(
            {
                "path": path,
                "date": date_name,
                "filename": filename
            }
        )


# ---------------------------------------------------------
# 既存レイアウト情報を再構築
# ---------------------------------------------------------

layout_groups = {}

for image_info in all_images:

    path = image_info["path"]

    try:

        signature = create_layout_signature(
            path
        )

    except Exception as e:

        print(
            f"レイアウト解析失敗: "
            f"{path} / {e}"
        )

        continue

    best_layout = None
    best_distance = 999


    # ---------------------------------------------
    # 既存レイアウトとの比較
    # ---------------------------------------------

    for layout_id, layout_info in layout_groups.items():

        reference_signature = (
            layout_info["signature"]
        )

        distance = calculate_layout_distance(
            signature,
            reference_signature
        )

        if distance < best_distance:

            best_distance = distance
            best_layout = layout_id


    # ---------------------------------------------
    # 同じレイアウト
    # ---------------------------------------------

    if (
        best_layout is not None
        and best_distance <= LAYOUT_THRESHOLD
    ):

        layout_id = best_layout

        layout_groups[
            layout_id
        ]["images"].append(
            {
                "date": image_info["date"],
                "filename": image_info["filename"]
            }
        )

        print(
            f"同一レイアウト: "
            f"{image_info['date']}/"
            f"{image_info['filename']} "
            f"→ {layout_id} "
            f"(距離 {best_distance:.1f})"
        )


    # ---------------------------------------------
    # 新しいレイアウト
    # ---------------------------------------------

    else:

        layout_number = (
            len(layout_groups) + 1
        )

        layout_id = (
            f"layout_{layout_number:03d}"
        )

        layout_groups[
            layout_id
        ] = {
            "signature": signature,
            "images": [
                {
                    "date": image_info["date"],
                    "filename": image_info["filename"]
                }
            ]
        }

        print(
            f"新規レイアウト: "
            f"{image_info['date']}/"
            f"{image_info['filename']} "
            f"→ {layout_id}"
        )


# =========================================================
# layout_index.json作成
# =========================================================

output_layout_data = {}

for layout_id, layout_info in layout_groups.items():

    output_layout_data[
        layout_id
    ] = {
        "images": layout_info["images"]
    }


with open(
    layout_index_file,
    "w",
    encoding="utf-8"
) as f:

    json.dump(
        output_layout_data,
        f,
        ensure_ascii=False,
        indent=2
    )


print()
print(
    f"layout_index.jsonを更新しました。"
)
print(
    f"検出したレイアウト数: "
    f"{len(output_layout_data)}"
)


# =========================================================
# 完了
# =========================================================

print()
print(f"保存先: {today_dir}")
print(
    f"保存先: {today_dir}"
)
print()
print("完了しました！")
print(
    "完了しました！"
)