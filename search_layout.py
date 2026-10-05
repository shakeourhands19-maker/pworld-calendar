import os
import json
import shutil
from datetime import datetime

from PIL import Image, ImageEnhance


# ============================================================
# 設定
# ============================================================

DATA_DIR = "data"

LAYOUT_INDEX_PATH = os.path.join(
    DATA_DIR,
    "layout_index.json"
)

LAYOUT_DIR = os.path.join(
    DATA_DIR,
    "layouts"
)

LAYOUT_IMAGE_SIZE = (64, 64)

LAYOUT_THRESHOLD = 18


# ============================================================
# フォルダ
# ============================================================

os.makedirs(
    LAYOUT_DIR,
    exist_ok=True
)


# ============================================================
# レイアウト署名
# ============================================================

def create_layout_signature(image_path):

    try:

        image = Image.open(
            image_path
        ).convert("L")

        image.thumbnail(
            LAYOUT_IMAGE_SIZE
        )

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

        canvas = ImageEnhance.Contrast(
            canvas
        ).enhance(1.5)

        pixels = list(
            canvas.get_flattened_data()
        )

        if not pixels:
            return None

        average = (
            sum(pixels)
            / len(pixels)
        )

        return [
            round(
                pixel - average,
                2
            )
            for pixel in pixels
        ]

    except Exception as e:

        print(
            f"画像処理エラー: "
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

    return sum(
        abs(a - b)
        for a, b in zip(
            signature1,
            signature2
        )
    ) / len(signature1)


# ============================================================
# layout_index.json
# ============================================================

def load_layout_index():

    if not os.path.exists(
        LAYOUT_INDEX_PATH
    ):

        print()
        print(
            "layout_index.jsonが見つかりません。"
        )

        return {}

    try:

        with open(
            LAYOUT_INDEX_PATH,
            "r",
            encoding="utf-8"
        ) as f:

            return json.load(f)

    except Exception as e:

        print()
        print(
            "layout_index.jsonの読み込みに失敗しました。"
        )
        print(e)

        return {}


# ============================================================
# 代表画像を自動作成
# ============================================================

def ensure_representative_images(
    layout_data
):

    created = 0

    for layout_id, layout_info in layout_data.items():

        representative_path = os.path.join(
            LAYOUT_DIR,
            layout_id + ".jpg"
        )

        if os.path.exists(
            representative_path
        ):
            continue

        images = layout_info.get(
            "images",
            []
        )

        for image_info in images:

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

            if not os.path.exists(
                source_path
            ):
                continue

            try:

                shutil.copy2(
                    source_path,
                    representative_path
                )

                print(
                    f"代表画像作成: "
                    f"{layout_id}.jpg"
                )

                created += 1

            except Exception as e:

                print(
                    f"代表画像作成失敗: "
                    f"{layout_id} / {e}"
                )

            break

    if created:

        print()
        print(
            f"代表画像を{created}件作成しました。"
        )


# ============================================================
# レイアウト一覧
# ============================================================

def show_layout_list(
    layout_data
):

    print()
    print(
        "============================================================"
    )
    print(
        "基本レイアウト一覧"
    )
    print(
        "============================================================"
    )

    if not layout_data:

        print(
            "登録されているレイアウトはありません。"
        )

        return

    for layout_id in sorted(
        layout_data.keys()
    ):

        layout = layout_data[
            layout_id
        ]

        images = layout.get(
            "images",
            []
        )

        print()
        print(
            f"{layout_id}"
        )
        print(
            f"  使用回数: {len(images)}回"
        )

        for image_info in images:

            if isinstance(
                image_info,
                dict
            ):

                print(
                    f"    "
                    f"{image_info.get('date', '')}"
                    f" / "
                    f"{image_info.get('filename', '')}"
                )

        representative = os.path.join(
            LAYOUT_DIR,
            layout_id + ".jpg"
        )

        print(
            f"  代表画像: "
            f"{'あり' if os.path.exists(representative) else 'なし'}"
        )


# ============================================================
# レイアウト詳細
# ============================================================

def show_layout_detail(
    layout_id,
    layout_data
):

    if layout_id not in layout_data:

        print()
        print(
            f"{layout_id} は存在しません。"
        )

        return

    layout = layout_data[
        layout_id
    ]

    images = layout.get(
        "images",
        []
    )

    print()
    print(
        "============================================================"
    )
    print(
        f"{layout_id} 詳細"
    )
    print(
        "============================================================"
    )

    print(
        f"使用回数: {len(images)}回"
    )

    representative = os.path.join(
        LAYOUT_DIR,
        layout_id + ".jpg"
    )

    print(
        f"代表画像: {representative}"
    )

    print()
    print(
        "使用履歴:"
    )

    for image_info in images:

        if isinstance(
            image_info,
            dict
        ):

            print(
                f"  "
                f"{image_info.get('date', '')}"
                f" / "
                f"{image_info.get('filename', '')}"
            )


# ============================================================
# 画像を全レイアウトと比較
# ============================================================

def search_layout_by_image(
    image_path,
    layout_data
):

    print()
    print(
        "============================================================"
    )
    print(
        "画像から基本レイアウトを検索"
    )
    print(
        "============================================================"
    )

    print()
    print(
        f"対象画像: {image_path}"
    )

    if not os.path.exists(
        image_path
    ):

        print()
        print(
            "画像が見つかりません。"
        )

        return

    target_signature = create_layout_signature(
        image_path
    )

    if target_signature is None:

        print(
            "対象画像の解析に失敗しました。"
        )

        return

    results = []

    for layout_id in sorted(
        layout_data.keys()
    ):

        representative = os.path.join(
            LAYOUT_DIR,
            layout_id + ".jpg"
        )

        if not os.path.exists(
            representative
        ):
            continue

        signature = create_layout_signature(
            representative
        )

        distance = calculate_layout_distance(
            target_signature,
            signature
        )

        results.append(
            (
                distance,
                layout_id
            )
        )

    results.sort(
        key=lambda x: x[0]
    )

    print()
    print(
        f"比較対象レイアウト数: {len(results)}"
    )

    if not results:

        print(
            "比較できる代表画像がありません。"
        )

        return

    print()
    print(
        "距離の近い順"
    )
    print(
        "------------------------------------------------------------"
    )

    for distance, layout_id in results:

        status = (
            "一致候補"
            if distance <= LAYOUT_THRESHOLD
            else ""
        )

        print(
            f"{layout_id} → "
            f"{distance:.2f}"
            + (
                f"  ★ {status}"
                if status
                else ""
            )
        )

    best_distance, best_layout = results[0]

    print()
    print(
        "------------------------------------------------------------"
    )

    if best_distance <= LAYOUT_THRESHOLD:

        print(
            f"最も近いレイアウト: "
            f"{best_layout}"
        )

        print(
            f"距離: {best_distance:.2f}"
        )

        images = layout_data[
            best_layout
        ].get(
            "images",
            []
        )

        print()
        print(
            "過去の使用履歴:"
        )

        for image_info in images:

            if isinstance(
                image_info,
                dict
            ):

                print(
                    f"  "
                    f"{image_info.get('date', '')}"
                    f" / "
                    f"{image_info.get('filename', '')}"
                )

    else:

        print(
            "既存レイアウトとの一致は"
            "確認できませんでした。"
        )

        print(
            f"最も近かったのは "
            f"{best_layout} "
            f"(距離 {best_distance:.2f})"
        )


# ============================================================
# 今日の画像一覧
# ============================================================

def get_today_images():

    today = datetime.now().strftime(
        "%Y-%m-%d"
    )

    today_dir = os.path.join(
        DATA_DIR,
        today
    )

    if not os.path.isdir(
        today_dir
    ):
        return []

    images = []

    for filename in sorted(
        os.listdir(today_dir)
    ):

        path = os.path.join(
            today_dir,
            filename
        )

        if not os.path.isfile(path):
            continue

        if filename.lower().endswith(
            (".jpg", ".jpeg", ".png", ".webp")
        ):

            images.append(
                (
                    filename,
                    path
                )
            )

    return images


# ============================================================
# 今日の画像から検索
# ============================================================

def search_today_image(
    layout_data
):

    today = datetime.now().strftime(
        "%Y-%m-%d"
    )

    images = get_today_images()

    print()
    print(
        f"今日 ({today}) の画像"
    )

    if not images:

        print(
            "今日の画像がありません。"
        )

        return

    for number, item in enumerate(
        images,
        start=1
    ):

        print(
            f"{number}: {item[0]}"
        )

    print()

    try:

        number = int(
            input(
                "比較する番号を入力してください: "
            ).strip()
        )

    except ValueError:

        print(
            "数字を入力してください。"
        )

        return

    if number < 1 or number > len(images):

        print(
            "番号が範囲外です。"
        )

        return

    filename, image_path = images[
        number - 1
    ]

    print()
    print(
        f"対象画像: {image_path}"
    )

    search_layout_by_image(
        image_path,
        layout_data
    )


# ============================================================
# 任意画像から検索
# ============================================================

def search_custom_image(
    layout_data
):

    print()

    image_path = input(
        "画像ファイルのパスを入力してください: "
    ).strip()

    image_path = image_path.strip(
        '"'
    )

    search_layout_by_image(
        image_path,
        layout_data
    )


# ============================================================
# メイン
# ============================================================

def main():

    layout_data = load_layout_index()

    if not layout_data:

        return

    # 代表画像がなければ自動作成
    ensure_representative_images(
        layout_data
    )

    show_layout_list(
        layout_data
    )

    while True:

        print()
        print(
            "============================================================"
        )
        print(
            "メニュー"
        )
        print(
            "============================================================"
        )
        print(
            "1 : レイアウト詳細を見る"
        )
        print(
            "2 : 指定した画像を全レイアウトと比較"
        )
        print(
            "3 : 今日の画像を全レイアウトと比較"
        )
        print(
            "0 : 終了"
        )
        print()

        choice = input(
            "番号を選択してください: "
        ).strip()

        if choice == "0":

            print()
            print(
                "終了します。"
            )

            break

        elif choice == "1":

            layout_id = input(
                "レイアウトIDを入力してください "
                "(例: layout_004): "
            ).strip()

            show_layout_detail(
                layout_id,
                layout_data
            )

        elif choice == "2":

            search_custom_image(
                layout_data
            )

        elif choice == "3":

            search_today_image(
                layout_data
            )

        else:

            print()
            print(
                "1、2、3、0 のいずれかを入力してください。"
            )


# ============================================================
# 実行
# ============================================================

if __name__ == "__main__":

    main()
