import json
import re
from pathlib import Path

import requests
from bs4 import BeautifulSoup


# ============================================================
# 設定
# ============================================================

# テストするみんレポのページ
TEST_URL = "https://min-repo.com/3249670/"

OUTPUT_DIR = Path("minrepo_data")


# ============================================================
# ページ取得
# ============================================================

headers = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/154.0.0.0 Safari/537.36"
    )
}

print("ページを取得しています...")
print(TEST_URL)

response = requests.get(
    TEST_URL,
    headers=headers,
    timeout=30
)

response.raise_for_status()

response.encoding = response.apparent_encoding

soup = BeautifulSoup(
    response.text,
    "html.parser"
)

print("取得成功")


# ============================================================
# タイトル・日付
# ============================================================

title = soup.find("h1")

if title:
    title_text = title.get_text(
        " ",
        strip=True
    )
else:
    title_text = ""

print()
print("タイトル:")
print(title_text)


# タイトルから日付を取得
#
# 例:
# 7/25(土) プレイランドハッピー手稲前田店
#
# 2025/11/29(土) ...
#

date_match = re.search(
    r"(\d{4}/)?(\d{1,2})/(\d{1,2})",
    title_text
)

if date_match:

    year_text = date_match.group(1)

    if year_text:
        year = int(year_text[:4])
    else:
        # 年が書かれていない場合は現在年
        from datetime import datetime
        year = datetime.now().year

    month = int(date_match.group(2))
    day = int(date_match.group(3))

    date = f"{year:04d}-{month:02d}-{day:02d}"

else:

    date = None


print()
print("営業日:")
print(date)


# ============================================================
# テキストから数値を取得する補助関数
# ============================================================

def clean_number(text):

    if text is None:
        return None

    text = text.strip()

    if text == "-":
        return None

    text = text.replace(",", "")

    # +123 / -123 / 123
    match = re.search(
        r"[-+]?\d+",
        text
    )

    if not match:
        return None

    return int(match.group())


# ============================================================
# 全体データ
# ============================================================

total_diff = None
average_diff = None
average_games = None
overall_win_rate = None


# ページ内の「総差枚」「平均差枚」などを探す
text = soup.get_text(
    "\n",
    strip=True
)

lines = [
    line.strip()
    for line in text.splitlines()
    if line.strip()
]


for i, line in enumerate(lines):

    if line == "総差枚" and i + 1 < len(lines):

        total_diff = clean_number(
            lines[i + 1]
        )

    elif line == "平均差枚" and i + 1 < len(lines):

        average_diff = clean_number(
            lines[i + 1]
        )

    elif line == "平均G数" and i + 1 < len(lines):

        average_games = clean_number(
            lines[i + 1]
        )

    elif line == "勝率" and i + 1 < len(lines):

        overall_win_rate = lines[i + 1]


print()
print("=== 店舗全体 ===")
print("総差枚 :", total_diff)
print("平均差枚 :", average_diff)
print("平均G数 :", average_games)
print("勝率 :", overall_win_rate)


# ============================================================
# テーブル取得
# ============================================================

tables = soup.find_all("table")

print()
print("テーブル数:", len(tables))


# ============================================================
# 機種別データ
# ============================================================

machines = []

for table in tables:

    rows = table.find_all("tr")

    if not rows:
        continue

    # ヘッダー
    header_cells = rows[0].find_all(
        ["th", "td"]
    )

    headers_text = [
        cell.get_text(
            " ",
            strip=True
        )
        for cell in header_cells
    ]

    header_text = " ".join(headers_text)

    # 機種別表か判定
    if not (
        "機種" in header_text
        and "平均差枚" in header_text
        and "平均G数" in header_text
        and "勝率" in header_text
        and "出率" in header_text
    ):
        continue

    for row in rows[1:]:

        cells = row.find_all(
            ["td", "th"]
        )

        values = [
            cell.get_text(
                " ",
                strip=True
            )
            for cell in cells
        ]

        if len(values) < 5:
            continue

        machine_name = values[0]

        if machine_name in [
            "機種",
            "差枚順",
            "G数順",
            "台数順"
        ]:
            continue

        machines.append(
            {
                "name": machine_name,
                "average_diff": clean_number(
                    values[1]
                ),
                "average_games": clean_number(
                    values[2]
                ),
                "win_rate": values[3],
                "payout_rate": values[4],
            }
        )

    break


print()
print("=== 機種別 ===")
print("取得件数:", len(machines))

for machine in machines[:5]:

    print(
        machine["name"],
        "|",
        machine["average_games"],
        "G |",
        machine["average_diff"],
        "枚 |",
        machine["win_rate"],
        "|",
        machine["payout_rate"]
    )


# ============================================================
# 末尾別データ
# ============================================================

tail_data = []

for table in tables:

    rows = table.find_all("tr")

    if not rows:
        continue

    header_cells = rows[0].find_all(
        ["th", "td"]
    )

    headers_text = [
        cell.get_text(
            " ",
            strip=True
        )
        for cell in header_cells
    ]

    header_text = " ".join(headers_text)

    # 末尾別表か判定
    if not (
        "末尾" in header_text
        and "平均差枚" in header_text
        and "平均G数" in header_text
        and "勝率" in header_text
        and "出率" in header_text
    ):
        continue

    for row in rows[1:]:

        cells = row.find_all(
            ["td", "th"]
        )

        values = [
            cell.get_text(
                " ",
                strip=True
            )
            for cell in cells
        ]

        if len(values) < 5:
            continue

        tail_data.append(
            {
                "tail": values[0],
                "average_diff": clean_number(
                    values[1]
                ),
                "average_games": clean_number(
                    values[2]
                ),
                "win_rate": values[3],
                "payout_rate": values[4],
            }
        )

    break


print()
print("=== 末尾別 ===")
print("取得件数:", len(tail_data))

for item in tail_data:

    print(
        item["tail"],
        "|",
        item["average_diff"],
        "枚 |",
        item["average_games"],
        "G |",
        item["win_rate"],
        "|",
        item["payout_rate"]
    )


# ============================================================
# JSON保存
# ============================================================

if date is None:

    print()
    print("日付を取得できなかったため保存を中止します。")

else:

    OUTPUT_DIR.mkdir(
        parents=True,
        exist_ok=True
    )

    result = {
        "date": date,
        "source_url": TEST_URL,
        "total_diff": total_diff,
        "average_diff": average_diff,
        "average_games": average_games,
        "overall_win_rate": overall_win_rate,
        "machines": machines,
        "tail": tail_data,
    }

    output_file = OUTPUT_DIR / f"{date}.json"

    with open(
        output_file,
        "w",
        encoding="utf-8"
    ) as f:

        json.dump(
            result,
            f,
            ensure_ascii=False,
            indent=2
        )

    print()
    print("================================")
    print("JSON保存完了")
    print(output_file)
    print("================================")
