import os
import re
import shutil
import subprocess
import json

from datetime import datetime
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup
from PIL import Image, ImageEnhance, ImageFilter


# ============================================================
# 設定
# ============================================================

PAGE_URL = (
    "https://www.p-world.co.jp/hokkaido/"
    "playland-happy-t.htm"
)

TESSERACT = "tesseract"

IMAGE_DIR = "downloaded_images"
DATA_DIR = "data"

# 基本レイアウトの代表画像保存先
LAYOUT_DIR = os.path.join(
    DATA_DIR,
    "layouts"
)


# ============================================================
# 採用キーワード
# ============================================================

KEYWORDS = [
    "開店",
    "OPEN",
]


# ============================================================
# 除外キーワード
#
# 「時差開放」「即時開放」は判定しない。
# ============================================================

EXCLUDE_KEYWORDS = [
    "抽選開始",
    "抽選への参加",
]


# ============================================================
# レイアウト判定設定
# ============================================================

LAYOUT_IMAGE_SIZE = (64, 64)

LAYOUT_THRESHOLD = 18


# ============================================================
# HTTP設定
# ============================================================

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/154.0.0.0 Safari/537.36"
    ),
    "Referer": "https://www.google.com/",
}


# ============================================================
# フォルダ作成
# ============================================================

os.makedirs(
    IMAGE_DIR,
    exist_ok=True
)

os.makedirs(
    DATA_DIR,
    exist_ok=True
)

os.makedirs(
    LAYOUT_DIR,
    exist_ok=True
)


# ============================================================
# レイアウト署名作成
# ============================================================

def create_layout_signature(image_path):

    try:

        image = Image.open(
            image_path
        ).convert("L")


        # ----------------------------------------------------
        # サムネイル化
        # ----------------------------------------------------

        image.thumbnail(
            LAYOUT_IMAGE_SIZE
        )


        # ----------------------------------------------------
        # 64×64の白背景に中央配置
        # ----------------------------------------------------

        canvas = Image.new(
            "L",
            LAYOUT_IMAGE_SIZE,
            255
        )

        x = (
            LAYOUT_IMAGE_SIZE[0]
            - image.width
        ) // 2

        y = (
            LAYOUT_IMAGE_SIZE[1]
            - image.height
        ) // 2

        canvas.paste(
            image,
            (x, y)
        )


        # ----------------------------------------------------
        # コントラスト強調
        # ----------------------------------------------------

        canvas = ImageEnhance.Contrast(
            canvas
        ).enhance(1.5)


        # ----------------------------------------------------
        # ピクセル取得
        # ----------------------------------------------------

        pixels = list(
            canvas.get_flattened_data()
        )

        if not pixels:
            return None


        # ----------------------------------------------------
        # 平均値で正規化
        # ----------------------------------------------------

        average = sum(pixels) / len(pixels)

        signature = [
            round(
                pixel - average,
                2
            )
            for pixel in pixels
        ]

        return signature


    except Exception as e:

        print(
            f"レイアウト署名作成エラー: "
            f"{image_path} / {e}"
        )

        return None


# ============================================================
# レイアウト距離
# ============================================================

def calculate_layout_distance(
    signature1,
    signature2
):

    if (
        signature1 is None
        or signature2 is None
    ):
        return 999999

    if len(signature1) != len(signature2):
        return 999999


    difference = sum(
        abs(a - b)
        for a, b in zip(
            signature1,
            signature2
        )
    ) / len(signature1)


    return difference


# ============================================================
# OCR用画像作成
# ============================================================

def create_ocr_images(
    image_path
):

    base_name = os.path.splitext(
        image_path
    )[0]


    image = Image.open(
        image_path
    ).convert("L")


    # ========================================================
    # 3倍に拡大
    # ========================================================

    width, height = image.size

    image = image.resize(
        (
            width * 3,
            height * 3
        ),
        Image.Resampling.LANCZOS
    )


    ocr_images = []


    # ========================================================
    # OCRパターン1
    # ========================================================

    image_normal = image.copy()

    image_normal = ImageEnhance.Contrast(
        image_normal
    ).enhance(2.0)

    image_normal = image_normal.filter(
        ImageFilter.SHARPEN
    )


    normal_path = (
        base_name
        + "_ocr_normal.png"
    )

    image_normal.save(
        normal_path
    )

    ocr_images.append(
        normal_path
    )


    # ========================================================
    # OCRパターン2
    # ========================================================

    image_contrast = image.copy()

    image_contrast = ImageEnhance.Contrast(
        image_contrast
    ).enhance(3.0)

    image_contrast = image_contrast.filter(
        ImageFilter.SHARPEN
    )

    image_contrast = image_contrast.filter(
        ImageFilter.SHARPEN
    )


    contrast_path = (
        base_name
        + "_ocr_contrast.png"
    )

    image_contrast.save(
        contrast_path
    )

    ocr_images.append(
        contrast_path
    )


    # ========================================================
    # OCRパターン3
    # ========================================================

    threshold = 180

    image_binary = image.copy()

    image_binary = image_binary.point(
        lambda p:
        255 if p > threshold else 0
    )


    binary_path = (
        base_name
        + "_ocr_binary.png"
    )

    image_binary.save(
        binary_path
    )

    ocr_images.append(
        binary_path
    )


    # ========================================================
    # OCRパターン4
    # ========================================================

    threshold_strong = 210

    image_binary_strong = image.copy()

    image_binary_strong = image_binary_strong.point(
        lambda p:
        255 if p > threshold_strong else 0
    )


    binary_strong_path = (
        base_name
        + "_ocr_binary_strong.png"
    )

    image_binary_strong.save(
        binary_strong_path
    )

    ocr_images.append(
        binary_strong_path
    )


    return ocr_images


# ============================================================
# Tesseract単体実行
# ============================================================

def run_single_ocr(
    image_path
):

    try:

        result = subprocess.run(
            [
                TESSERACT,
                image_path,
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
            timeout=15,
        )

        return result.stdout or ""


    except Exception as e:

        print(
            f"OCRエラー: "
            f"{image_path} / {e}"
        )

        return ""


# ============================================================
# OCR実行
# ============================================================

def run_ocr(
    image_path
):

    ocr_images = []

    try:

        ocr_images = create_ocr_images(
            image_path
        )

        results = []


        # ----------------------------------------------------
        # 4パターンOCR
        # ----------------------------------------------------

        for ocr_image in ocr_images:

            text = run_single_ocr(
                ocr_image
            )

            if text.strip():

                results.append(
                    text
                )


        # ----------------------------------------------------
        # OCR結果を結合
        # ----------------------------------------------------

        return "\n".join(
            results
        )


    except Exception as e:

        print(
            f"OCR処理エラー: "
            f"{image_path} / {e}"
        )

        return ""


    finally:

        # ----------------------------------------------------
        # OCR用一時ファイル削除
        # ----------------------------------------------------

        for ocr_image in ocr_images:

            if os.path.exists(
                ocr_image
            ):

                try:

                    os.remove(
                        ocr_image
                    )

                except Exception:

                    pass


# ============================================================
# OCR文字の簡易正規化
# ============================================================

def normalize_ocr_text(
    text
):

    if not text:
        return ""


    text = text.replace(
        "\r",
        ""
    )

    text = text.replace(
        "\n",
        ""
    )

    text = text.replace(
        " ",
        ""
    )

    text = text.replace(
        "　",
        ""
    )


    return text.lower()


# ============================================================
# P-WORLDページ取得
# ============================================================

print(
    "P-WORLDページを取得しています..."
)


try:

    response = requests.get(
        PAGE_URL,
        headers=HEADERS,
        timeout=30
    )

    response.raise_for_status()


except Exception as e:

    print(
        f"ページ取得失敗: {e}"
    )

    raise SystemExit


print(
    "ページ取得成功"
)


# ============================================================
# HTML解析
# ============================================================

soup = BeautifulSoup(
    response.text,
    "html.parser"
)


# ============================================================
# 告知画像URL取得
# ============================================================

image_urls = []


for img in soup.find_all(
    "img"
):

    src = (
        img.get("src")
        or img.get("data-src")
        or img.get("data-original")
    )


    if not src:
        continue


    full_url = urljoin(
        PAGE_URL,
        src
    )


    # --------------------------------------------------------
    # P-WORLDの画像を対象
    # --------------------------------------------------------

    if (
        "img_warehouse" in full_url
        or "img" in full_url.lower()
    ):

        if full_url not in image_urls:

            image_urls.append(
                full_url
            )


print()

print(
    f"告知画像を "
    f"{len(image_urls)} 枚発見しました。"
)


# ============================================================
# 今日の日付
# ============================================================

today = datetime.now().strftime(
    "%Y-%m-%d"
)


today_dir = os.path.join(
    DATA_DIR,
    today
)


os.makedirs(
    today_dir,
    exist_ok=True
)


print()

print(
    f"保存先: {today_dir}"
)


# ============================================================
# 今日の画像処理
# ============================================================

matched_files = []


for i, image_url in enumerate(
    image_urls,
    start=1
):

    # ========================================================
    # 拡張子判定
    # ========================================================

    extension = ".jpg"

    lower_url = image_url.lower()


    if ".png" in lower_url:

        extension = ".png"


    elif ".gif" in lower_url:

        extension = ".gif"


    elif ".webp" in lower_url:

        extension = ".webp"


    filename = (
        f"{i:02d}"
        + extension
    )


    downloaded_path = os.path.join(
        IMAGE_DIR,
        filename
    )


    # ========================================================
    # ダウンロード
    # ========================================================

    try:

        image_response = requests.get(
            image_url,
            headers=HEADERS,
            timeout=30
        )

        image_response.raise_for_status()


        with open(
            downloaded_path,
            "wb"
        ) as f:

            f.write(
                image_response.content
            )


    except Exception as e:

        print()

        print(
            f"[{i}/{len(image_urls)}] "
            f"{filename} → "
            f"ダウンロード失敗: {e}"
        )

        continue


    # ========================================================
    # OCR
    # ========================================================

    ocr_text = run_ocr(
        downloaded_path
    )


    normalized_text = normalize_ocr_text(
        ocr_text
    )


    # ========================================================
    # OCR結果表示
    # ========================================================

    print()

    print(
        f"----- OCR結果: {filename} -----"
    )


    if ocr_text.strip():

        print(
            ocr_text.strip()
        )


    else:

        print(
            "(OCR結果なし)"
        )


    print(
        "--------------------------------"
    )


    # ========================================================
    # 除外判定
    # ========================================================

    exclude_hits = []


    for keyword in EXCLUDE_KEYWORDS:

        if keyword.lower() in normalized_text:

            exclude_hits.append(
                keyword
            )


    # ========================================================
    # 除外
    # ========================================================

    if exclude_hits:

        print()

        print(
            f"[{i}/{len(image_urls)}] "
            f"{filename} → 除外（"
            f"{', '.join(exclude_hits)}"
            f"）"
        )

        continue


    # ========================================================
    # 採用判定
    # ========================================================

    matched_keywords = []


    for keyword in KEYWORDS:

        if keyword.lower() in normalized_text:

            matched_keywords.append(
                keyword
            )


    # ========================================================
    # 採用
    # ========================================================

    if matched_keywords:

        destination = os.path.join(
            today_dir,
            filename
        )


        shutil.copy2(
            downloaded_path,
            destination
        )


        matched_files.append(
            filename
        )


        print()

        print(
            f"[{i}/{len(image_urls)}] "
            f"{filename} → 採用（"
            f"{', '.join(matched_keywords)}"
            f"）"
        )


    # ========================================================
    # 該当なし
    # ========================================================

    else:

        print()

        print(
            f"[{i}/{len(image_urls)}] "
            f"{filename} → 該当なし"
        )


# ============================================================
# 本日の結果
# ============================================================

print()

print(
    "============================================================"
)

print(
    "本日の判定結果"
)

print(
    "============================================================"
)


if matched_files:

    print(
        f"対象画像: "
        f"{len(matched_files)} 枚"
    )


    for filename in matched_files:

        print(
            f"  {filename}"
        )


else:

    print(
        "対象画像は見つかりませんでした。"
    )


# ============================================================
# layout_index.json
# ============================================================

print()

print(
    "============================================================"
)

print(
    "基本レイアウト判定"
)

print(
    "============================================================"
)


layout_index_path = os.path.join(
    DATA_DIR,
    "layout_index.json"
)


# ============================================================
# 既存layout_index.json読み込み
# ============================================================

layout_data = {}


if os.path.exists(
    layout_index_path
):

    try:

        with open(
            layout_index_path,
            "r",
            encoding="utf-8"
        ) as f:

            layout_data = json.load(
                f
            )

    except Exception as e:

        print(
            f"既存layout_index.jsonの読み込み失敗: {e}"
        )

        layout_data = {}


# ============================================================
# 既存レイアウトの署名を復元
#
# 既存JSONには署名を保存していないため、
# 代表画像から再計算する。
# ============================================================

layout_groups = []


for layout_id, layout_info in layout_data.items():

    images = layout_info.get(
        "images",
        []
    )


    if not images:
        continue


    # --------------------------------------------------------
    # 代表画像を探す
    # --------------------------------------------------------

    representative_path = None


    for image_info in images:

        if isinstance(
            image_info,
            dict
        ):

            date = image_info.get(
                "date"
            )

            filename = image_info.get(
                "filename"
            )

            if date and filename:

                candidate = os.path.join(
                    DATA_DIR,
                    date,
                    filename
                )

                if os.path.exists(
                    candidate
                ):

                    representative_path = candidate

                    break


        else:

            # 旧形式への対応
            candidate = os.path.join(
                DATA_DIR,
                image_info
            )

            if os.path.exists(
                candidate
            ):

                representative_path = candidate

                break


    if not representative_path:

        continue


    signature = create_layout_signature(
        representative_path
    )


    if signature is None:
        continue


    layout_groups.append(
        {
            "id": layout_id,
            "signature": signature,
            "images": images,
        }
    )


# ============================================================
# layout番号の最大値を取得
# ============================================================

max_layout_number = 0


for layout in layout_groups:

    match = re.search(
        r"layout_(\d+)",
        layout["id"]
    )


    if match:

        number = int(
            match.group(1)
        )

        max_layout_number = max(
            max_layout_number,
            number
        )


# ============================================================
# data以下から「今日の採用画像」を取得
#
# レイアウト検索対象は採用画像だけ。
# ============================================================

today_images = []


for filename in matched_files:

    full_path = os.path.join(
        today_dir,
        filename
    )


    if os.path.exists(
        full_path
    ):

        today_images.append(
            (
                filename,
                full_path
            )
        )


# ============================================================
# 今日の画像を既存レイアウトと比較
# ============================================================

for filename, full_path in today_images:

    signature = create_layout_signature(
        full_path
    )


    if signature is None:

        continue


    matched_layout = None

    matched_distance = None


    # ========================================================
    # 既存レイアウトを検索
    # ========================================================

    for layout in layout_groups:

        distance = calculate_layout_distance(
            signature,
            layout["signature"]
        )


        if distance <= LAYOUT_THRESHOLD:

            matched_layout = layout

            matched_distance = distance

            break


    # ========================================================
    # 既存レイアウトに追加
    # ========================================================

    if matched_layout:

        image_entry = {
            "date": today,
            "filename": filename
        }


        # 同じ画像が既に登録されていないか確認
        already_exists = False


        for existing in matched_layout["images"]:

            if (
                isinstance(existing, dict)
                and existing.get("date") == today
                and existing.get("filename") == filename
            ):

                already_exists = True

                break


        if not already_exists:

            matched_layout["images"].append(
                image_entry
            )


        print(
            f"既存レイアウト: "
            f"{today}/{filename} → "
            f"{matched_layout['id']} "
            f"(距離 {matched_distance:.1f})"
        )


    # ========================================================
    # 新規レイアウト
    # ========================================================

    else:

        max_layout_number += 1


        layout_id = (
            f"layout_"
            f"{max_layout_number:03d}"
        )


        new_layout = {
            "id": layout_id,
            "signature": signature,
            "images": [
                {
                    "date": today,
                    "filename": filename
                }
            ]
        }


        layout_groups.append(
            new_layout
        )


        print(
            f"新規レイアウト: "
            f"{today}/{filename} → "
            f"{layout_id}"
        )


        # ----------------------------------------------------
        # 代表画像保存
        # ----------------------------------------------------

        representative_path = os.path.join(
            LAYOUT_DIR,
            layout_id + ".jpg"
        )


        try:

            shutil.copy2(
                full_path,
                representative_path
            )


        except Exception as e:

            print(
                f"代表画像保存失敗: "
                f"{representative_path} / {e}"
            )


# ============================================================
# 既存レイアウトの代表画像がない場合も補完
# ============================================================

for layout in layout_groups:

    representative_path = os.path.join(
        LAYOUT_DIR,
        layout["id"] + ".jpg"
    )


    if os.path.exists(
        representative_path
    ):
        continue


    for image_info in layout["images"]:

        if not isinstance(
            image_info,
            dict
        ):
            continue


        date = image_info.get(
            "date"
        )

        filename = image_info.get(
            "filename"
        )


        if not date or not filename:
            continue


        source_path = os.path.join(
            DATA_DIR,
            date,
            filename
        )


        if os.path.exists(
            source_path
        ):

            try:

                shutil.copy2(
                    source_path,
                    representative_path
                )

                print(
                    f"代表画像作成: "
                    f"{layout['id']}.jpg"
                )

            except Exception as e:

                print(
                    f"代表画像作成失敗: "
                    f"{layout['id']} / {e}"
                )

            break


# ============================================================
# layout_index.json保存
# ============================================================

output_layout_data = {}


for layout in layout_groups:

    output_layout_data[
        layout["id"]
    ] = {
        "images": layout["images"]
    }


with open(
    layout_index_path,
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
    "layout_index.jsonを更新しました。"
)


print(
    f"検出したレイアウト数: "
    f"{len(layout_groups)}"
)


# ============================================================
# レイアウト一覧表示
# ============================================================

print()

print(
    "============================================================"
)

print(
    "レイアウト一覧"
)

print(
    "============================================================"
)


for layout in layout_groups:

    print(
        f"{layout['id']} : "
        f"{len(layout['images'])}枚"
    )


    for image_info in layout["images"]:

        if isinstance(
            image_info,
            dict
        ):

            print(
                f"    {image_info['date']} / "
                f"{image_info['filename']}"
            )


# ============================================================
# 完了
# ============================================================

print()

print(
    f"保存先: {today_dir}"
)

print()

print(
    "完了しました！"
)
