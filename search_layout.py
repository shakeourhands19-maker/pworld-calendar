import os
import json

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
        # 64×64白背景
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
        # コントラスト
        # ----------------------------------------------------

        canvas = ImageEnhance.Contrast(
            canvas
        ).enhance(1.5)


        # ----------------------------------------------------
        # ピクセル
        # ----------------------------------------------------

        pixels = list(
            canvas.get_flattened_data()
        )


        if not pixels:

            return None


        # ----------------------------------------------------
        # 平均値で正規化
        # ----------------------------------------------------

        average = (
            sum(pixels)
            / len(pixels)
        )


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
            f"画像処理エラー: "
            f"{image_path}"
        )

        print(e)

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
# layout_index.json読み込み
# ============================================================

def load_layout_index():

    if not os.path.exists(
        LAYOUT_INDEX_PATH
    ):

        print()

        print(
            "layout_index.jsonが見つかりません。"
        )

        print(
            f"確認場所: {LAYOUT_INDEX_PATH}"
        )

        return {}


    try:

        with open(
            LAYOUT_INDEX_PATH,
            "r",
            encoding="utf-8"
        ) as f:

            return json.load(
                f
            )


    except Exception as e:

        print()

        print(
            "layout_index.jsonの読み込みに失敗しました。"
        )

        print(e)

        return {}


# ============================================================
# レイアウト一覧表示
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


        if images:

            print(
                "  使用日:"
            )


            for image_info in images:

                if isinstance(
                    image_info,
                    dict
                ):

                    date = image_info.get(
                        "date",
                        ""
                    )

                    filename = image_info.get(
                        "filename",
                        ""
                    )


                    print(
                        f"    {date} / {filename}"
                    )


                else:

                    print(
                        f"    {image_info}"
                    )


        representative = os.path.join(
            LAYOUT_DIR,
            layout_id + ".jpg"
        )


        if os.path.exists(
            representative
        ):

            print(
                f"  代表画像: {representative}"
            )

        else:

            print(
                "  代表画像: なし"
            )


# ============================================================
# レイアウト詳細表示
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


    print()

    print(
        f"使用回数: {len(images)}回"
    )


    print()

    print(
        "代表画像:"
    )


    representative = os.path.join(
        LAYOUT_DIR,
        layout_id + ".jpg"
    )


    print(
        f"  {representative}"
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

            date = image_info.get(
                "date",
                ""
            )

            filename = image_info.get(
                "filename",
                ""
            )


            print(
                f"  {date} / {filename}"
            )

        else:

            print(
                f"  {image_info}"
            )


# ============================================================
# 画像からレイアウト検索
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
        f"検索画像: {image_path}"
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

        print()

        print(
            "検索画像の解析に失敗しました。"
        )

        return


    results = []


    # ========================================================
    # 全レイアウトと比較
    # ========================================================

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


        if signature is None:

            continue


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


    # ========================================================
    # 距離順
    # ========================================================

    results.sort(
        key=lambda x: x[0]
    )


    if not results:

        print()

        print(
            "比較できるレイアウトがありません。"
        )

        return


    print()

    print(
        "近いレイアウト"
    )

    print(
        "------------------------------------------------------------"
    )


    # 上位5件表示

    for distance, layout_id in results[:5]:

        if distance <= LAYOUT_THRESHOLD:

            status = "一致候補"

        else:

            status = "参考"


        print(
            f"{layout_id} : "
            f"距離 {distance:.1f} "
            f"→ {status}"
        )


    # ========================================================
    # 最も近いレイアウト
    # ========================================================

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
            f"距離: {best_distance:.1f}"
        )


        layout = layout_data[
            best_layout
        ]


        images = layout.get(
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
            f"(距離 {best_distance:.1f})"
        )


# ============================================================
# メイン
# ============================================================

def main():

    layout_data = load_layout_index()


    if not layout_data:

        return


    # ========================================================
    # 一覧表示
    # ========================================================

    show_layout_list(
        layout_data
    )


    # ========================================================
    # メニュー
    # ========================================================

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
            "2 : 画像からレイアウトを検索"
        )

        print(
            "0 : 終了"
        )

        print()


        choice = input(
            "番号を入力してください: "
        ).strip()


        # ====================================================
        # 終了
        # ====================================================

        if choice == "0":

            print()

            print(
                "終了します。"
            )

            break


        # ====================================================
        # レイアウト詳細
        # ====================================================

        elif choice == "1":

            print()

            layout_id = input(
                "レイアウトIDを入力してください "
                "(例: layout_004): "
            ).strip()


            show_layout_detail(
                layout_id,
                layout_data
            )


        # ====================================================
        # 画像検索
        # ====================================================

        elif choice == "2":

            print()

            image_path = input(
                "画像ファイルのパスを入力してください: "
            ).strip()


            # ダブルクォーテーションを除去
            image_path = image_path.strip(
                '"'
            )


            search_layout_by_image(
                image_path,
                layout_data
            )


        # ====================================================
        # その他
        # ====================================================

        else:

            print()

            print(
                "1、2、0 のいずれかを入力してください。"
            )


# ============================================================
# 実行
# ============================================================

if __name__ == "__main__":

    main()
