import os
import re
import json
import time
from datetime import datetime, timedelta

import requests
from bs4 import BeautifulSoup
from playwright.sync_api import sync_playwright


# ============================================================
# 設定
# ============================================================

TAG_URL = (
    "https://min-repo.com/tag/"
    "%E3%83%97%E3%83%AC%E3%82%A4%E3%83%A9%E3%83%B3%E3%83%89"
    "%E3%83%8F%E3%83%83%E3%83%94%E3%83%BC"
    "%E6%89%8B%E7%A8%B2%E5%89%8D%E7%94%B0%E5%BA%97/"
)

STORE_NAME = "プレイランドハッピー手稲前田店"

DATA_DIR = "minrepo_data"
EXCLUDED_FILE = "excluded_urls.json"

# 0 = 全履歴
MAX_NEW_DAYS = 3

# 待機時間
PAGE_WAIT = 5
REPORT_WAIT = 5


# ============================================================
# ヘッダー
# ============================================================

MACHINE_HEADER = [
    "機種",
    "平均差枚",
    "平均G数",
    "勝率",
    "出率",
]

NUMBER_HEADER = [
    "機種",
    "台番",
    "差枚",
    "G数",
    "出率",
]

TAIL_HEADER = [
    "末尾",
    "平均差枚",
    "平均G数",
    "勝率",
    "出率",
]


# ============================================================
# 共通
# ============================================================

def get_row_values(row):
    return [
        cell.get_text(" ", strip=True)
        for cell in row.find_all(["th", "td"])
    ]


def find_table_by_header(tables, target_header):

    for table in tables:

        for row in table.find_all("tr"):

            cells = get_row_values(row)

            if cells[:5] == target_header:
                return table

    return None


def clean_number(value):

    if value is None:
        return None

    value = value.strip()

    if value in ("", "-"):
        return None

    value = value.replace(",", "")
    value = value.replace("+", "")

    try:
        return int(value)

    except ValueError:
        return value


# ============================================================
# 対象店舗判定
# ============================================================

def is_target_store(soup):

    title = soup.title.get_text(" ", strip=True) if soup.title else ""

    if STORE_NAME in title:
        return True

    # タイトルに店舗名がない場合だけ本文も確認
    text = soup.get_text(" ", strip=True)

    return STORE_NAME in text


# ============================================================
# レポートURL収集
# ============================================================

DATE_ONLY_PATTERN = re.compile(
    r"^(?:\d{4}/)?\d{1,2}/\d{1,2}"
    r"\([月火水木金土日]\)$"
)


def collect_report_urls(page):

    urls = {}

    page_no = 1

    while True:

        if page_no == 1:
            url = TAG_URL
        else:
            url = TAG_URL.rstrip("/") + f"/page/{page_no}/"

        print(f"タグページ {page_no} を確認中...")

        try:

            page.goto(
                url,
                wait_until="domcontentloaded",
                timeout=30000,
            )

            time.sleep(PAGE_WAIT)

        except Exception as e:

            print(f"  タグページ取得失敗: {e}")
            break

        soup = BeautifulSoup(page.content(), "html.parser")

        found_this_page = 0
        total_this_page = 0
        excluded_store_links = 0

        for a in soup.find_all("a", href=True):

            href = a["href"].strip()

            if not re.match(
                r"^https://min-repo\.com/\d+/$",
                href,
            ):
                continue

            text = a.get_text(" ", strip=True)

            if not text:
                continue

            total_this_page += 1

            # ------------------------------------------------
            # ★重要
            #
            # 「10/3(土)」のように日付だけのリンクだけ採用
            #
            # 「10/3(土) アミューズイチゴ」
            # のような店舗名付きリンクは別店舗なので除外
            # ------------------------------------------------

            if not DATE_ONLY_PATTERN.match(text):

                excluded_store_links += 1
                continue

            if href not in urls:

                urls[href] = {
                    "date_text": text,
                }

                found_this_page += 1

        print(
            f"  レポート {total_this_page}件 / "
            f"対象 {found_this_page}件 / "
            f"店舗名付き除外 {excluded_store_links}件"
        )

        # 新しいURLがなくなったら終了
        if found_this_page == 0:

            print("  新規対象URLがなくなったため終了")
            break

        page_no += 1

        if page_no > 200:

            print("  ページ数上限に到達")
            break

    return urls


# ============================================================
# 日付
# ============================================================

def parse_date(text):

    text = text.strip()

    # 2026/10/3(土)
    m = re.match(
        r"(\d{4})/(\d{1,2})/(\d{1,2})",
        text,
    )

    if m:

        return datetime(
            int(m.group(1)),
            int(m.group(2)),
            int(m.group(3)),
        ).date()

    # 10/3(土)
    m = re.match(
        r"(\d{1,2})/(\d{1,2})",
        text,
    )

    if m:

        month = int(m.group(1))
        day = int(m.group(2))

        today = datetime.now().date()

        year = today.year

        # 年をまたぐ場合
        candidate = datetime(
            year,
            month,
            day,
        ).date()

        # 未来の日付になった場合は前年
        if candidate > today + timedelta(days=7):
            year -= 1

        return datetime(
            year,
            month,
            day,
        ).date()

    return None


# ============================================================
# 既存JSON
# ============================================================

def load_existing_dates():

    os.makedirs(DATA_DIR, exist_ok=True)

    dates = set()

    for filename in os.listdir(DATA_DIR):

        if not filename.endswith(".json"):
            continue

        if filename == "index.json":
            continue

        if re.match(
            r"^\d{4}-\d{2}-\d{2}\.json$",
            filename,
        ):

            dates.add(
                filename[:-5]
            )

    return dates


# ============================================================
# 除外URL
# ============================================================

def load_excluded_urls():

    if not os.path.exists(EXCLUDED_FILE):
        return set()

    try:

        with open(
            EXCLUDED_FILE,
            "r",
            encoding="utf-8",
        ) as f:

            data = json.load(f)

        if isinstance(data, list):
            return set(data)

        if isinstance(data, dict):
            return set(data.keys())

    except Exception:
        pass

    return set()


def save_excluded_urls(urls):

    with open(
        EXCLUDED_FILE,
        "w",
        encoding="utf-8",
    ) as f:

        json.dump(
            sorted(urls),
            f,
            ensure_ascii=False,
            indent=2,
        )


# ============================================================
# 全体データ
# ============================================================

def extract_overall(soup):

    text = soup.get_text(" ", strip=True)

    result = {
        "総差枚": None,
        "平均差枚": None,
        "平均G数": None,
        "勝率": None,
    }

    patterns = {
        "総差枚": r"総差枚\s*([+\-]?\d[\d,]*)",
        "平均差枚": r"平均差枚\s*([+\-]?\d[\d,]*)",
        "平均G数": r"平均G数\s*([\d,]+)",
        "勝率": r"勝率\s*(\d+\s*/\s*\d+)",
    }

    for key, pattern in patterns.items():

        m = re.search(pattern, text)

        if m:
            result[key] = clean_number(
                m.group(1)
            )

    return result


# ============================================================
# 機種別
# ============================================================

def extract_machine_data(soup):

    tables = soup.find_all("table")

    table = find_table_by_header(
        tables,
        MACHINE_HEADER,
    )

    if table is None:
        return []

    rows = []

    for tr in table.find_all("tr"):

        cells = get_row_values(tr)

        if cells[:5] == MACHINE_HEADER:
            continue

        if len(cells) < 5:
            continue

        machine = cells[0].strip()

        if not machine:
            continue

        if "バラエティ" in machine:
            continue

        if "1台設置" in machine:
            continue

        rows.append({
            "機種": machine,
            "平均差枚": clean_number(cells[1]),
            "平均G数": clean_number(cells[2]),
            "勝率": cells[3].strip(),
            "出率": cells[4].strip(),
        })

    # 平均G数の降順
    rows.sort(
        key=lambda x:
        x["平均G数"]
        if isinstance(x["平均G数"], int)
        else -1,
        reverse=True,
    )

    return rows


# ============================================================
# 台番号別
# ============================================================

def extract_number_data(soup):

    tables = soup.find_all("table")

    table = find_table_by_header(
        tables,
        NUMBER_HEADER,
    )

    if table is None:
        return []

    rows = []

    for tr in table.find_all("tr"):

        cells = get_row_values(tr)

        if cells[:5] == NUMBER_HEADER:
            continue

        if len(cells) < 5:
            continue

        machine = cells[0].strip()
        number = cells[1].strip()

        if not machine:
            continue

        if not re.fullmatch(r"\d+", number):
            continue

        rows.append({
            "機種": machine,
            "台番": int(number),
            "差枚": clean_number(cells[2]),
            "G数": clean_number(cells[3]),
            "出率": cells[4].strip(),
        })

    return rows


# ============================================================
# 末尾
# ============================================================

def extract_tail_data(soup):

    tables = soup.find_all("table")

    table = find_table_by_header(
        tables,
        TAIL_HEADER,
    )

    if table is None:
        return []

    rows = []

    for tr in table.find_all("tr"):

        cells = get_row_values(tr)

        if cells[:5] == TAIL_HEADER:
            continue

        if len(cells) < 5:
            continue

        tail = cells[0].strip()

        if not tail:
            continue

        rows.append({
            "末尾": tail,
            "平均差枚": clean_number(cells[1]),
            "平均G数": clean_number(cells[2]),
            "勝率": cells[3].strip(),
            "出率": cells[4].strip(),
        })

    return rows


# ============================================================
# レポート取得
# ============================================================

def fetch_report(page, url):

    try:

        page.goto(
            url,
            wait_until="domcontentloaded",
            timeout=60000,
        )

        time.sleep(REPORT_WAIT)

        soup = BeautifulSoup(
            page.content(),
            "html.parser",
        )

        # 店舗確認
        if not is_target_store(soup):
    print("  → 別店舗判定")
    print("  title:", soup.title.get_text(" ", strip=True) if soup.title else "(なし)")
    print("  店舗名あり:", STORE_NAME in soup.get_text(" ", strip=True))
    return {"status":"other_store"}

        # データ抽出
        overall = extract_overall(soup)
        machine_data = extract_machine_data(soup)
        number_data = extract_number_data(soup)
        tail_data = extract_tail_data(soup)

        # データなし
        if (
            not machine_data
            and not number_data
            and not tail_data
        ):

            return {
                "status": "no_data"
            }

        return {
            "status": "success",
            "overall": overall,
            "machine_data": machine_data,
            "number_data": number_data,
            "tail_data": tail_data,
        }

    except Exception as e:

        return {
            "status": "error",
            "error": str(e),
        }


# ============================================================
# メイン
# ============================================================

def main():

    os.makedirs(DATA_DIR, exist_ok=True)

    print("=" * 50)
    print("みんレポ収集開始")
    print("=" * 50)

    existing_dates = load_existing_dates()
    excluded_urls = load_excluded_urls()

    with sync_playwright() as p:

        browser = p.chromium.launch(
            headless=True
        )

        page = browser.new_page()

        # ----------------------------------------------------
        # URL収集
        # ----------------------------------------------------

        report_urls = collect_report_urls(page)

        print()
        print("=" * 50)
        print("URL収集完了")
        print("=" * 50)

        print(
            f"対象レポート : {len(report_urls)}"
        )

        print(
            f"既存データ   : {len(existing_dates)}"
        )

        # ----------------------------------------------------
        # 新規候補
        # ----------------------------------------------------

        candidates = []

        for url, info in report_urls.items():

            if url in excluded_urls:
                continue

            report_date = parse_date(
                info["date_text"]
            )

            if report_date is None:
                continue

            date_str = report_date.isoformat()

            if date_str in existing_dates:
                continue

            candidates.append({
                "url": url,
                "date": report_date,
            })

        # 日付順
        candidates.sort(
            key=lambda x: x["date"]
        )

        # MAX_NEW_DAYS
        if MAX_NEW_DAYS > 0:
            candidates = candidates[
                -MAX_NEW_DAYS:
            ]

        print(
            f"新規取得候補 : {len(candidates)}"
        )

        print()

        # ----------------------------------------------------
        # 統計
        # ----------------------------------------------------

        success = 0
        skipped = len(report_urls) - len(candidates)
        other_store = 0
        errors = 0
        no_data = 0

        retry_candidates = []

        # ----------------------------------------------------
        # 取得
        # ----------------------------------------------------

        try:

            for i, item in enumerate(
                candidates,
                1,
            ):

                url = item["url"]
                report_date = item["date"]
                date_str = report_date.isoformat()

                print(
                    f"[{i}/{len(candidates)}] "
                    f"{date_str} "
                    f"{url}"
                )

                result = fetch_report(
                    page,
                    url,
                )

                status = result["status"]

                # --------------------------------------------
                # 成功
                # --------------------------------------------

                if status == "success":

                    data = {
                        "date": date_str,
                        "store": STORE_NAME,
                        "url": url,
                        "overall": result["overall"],
                        "machine_data": result["machine_data"],
                        "number_data": result["number_data"],
                        "tail_data": result["tail_data"],
                    }

                    filepath = os.path.join(
                        DATA_DIR,
                        f"{date_str}.json",
                    )

                    with open(
                        filepath,
                        "w",
                        encoding="utf-8",
                    ) as f:

                        json.dump(
                            data,
                            f,
                            ensure_ascii=False,
                            indent=2,
                        )

                    success += 1
                    existing_dates.add(date_str)

                    print(
                        f"  → 成功 "
                        f"(機種 {len(result['machine_data'])}件 / "
                        f"台番号 {len(result['number_data'])}件 / "
                        f"末尾 {len(result['tail_data'])}件)"
                    )

                # --------------------------------------------
                # 別店舗
                # --------------------------------------------

                elif status == "other_store":

                    other_store += 1
                    excluded_urls.add(url)

                    print(
                        "  → 別店舗"
                    )

                # --------------------------------------------
                # データなし
                # --------------------------------------------

                elif status == "no_data":

                    no_data += 1

                    retry_candidates.append({
                        "date": date_str,
                        "url": url,
                    })

                    print(
                        "  → データなし"
                    )

                # --------------------------------------------
                # 取得失敗
                # --------------------------------------------

                else:

                    errors += 1

                    retry_candidates.append({
                        "date": date_str,
                        "url": url,
                    })

                    print(
                        f"  → 取得失敗: "
                        f"{result.get('error', '')}"
                    )

        except KeyboardInterrupt:

            print()
            print(
                "Ctrl+C が押されたため中断しました。"
            )

        finally:

            save_excluded_urls(
                excluded_urls
            )

            browser.close()

    # ========================================================
    # 結果
    # ========================================================

    print()
    print("=" * 50)
    print("取得結果")
    print("=" * 50)

    print(
        f"対象レポート : {len(report_urls)}"
    )

    print(
        f"成功         : {success}"
    )

    print(
        f"既存スキップ : {skipped}"
    )

    print(
        f"別店舗       : {other_store}"
    )

    print(
        f"取得失敗     : {errors}"
    )

    print(
        f"データなし   : {no_data}"
    )

    # ========================================================
    # 再取得候補
    # ========================================================

    if retry_candidates:

        print()
        print("=" * 50)
        print("再取得候補")
        print("=" * 50)

        for item in retry_candidates:

            print(
                f"{item['date']} | "
                f"{item['url']}"
            )

    print()
    print("処理終了")


if __name__ == "__main__":
    main()
