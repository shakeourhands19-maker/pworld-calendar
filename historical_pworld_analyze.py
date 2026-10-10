import csv
import json
import re
import subprocess
from pathlib import Path
from datetime import datetime

ROOT = Path("historical_probe_retry")
INDEX = ROOT / "index.json"
REPORT = ROOT / "historical_analysis"
REPORT.mkdir(parents=True, exist_ok=True)
CSV_PATH = REPORT / "date_candidates.csv"
TXT_PATH = REPORT / "ocr_text.txt"

def ocr(path):
    try:
        p = subprocess.run(
            ["tesseract", str(path), "stdout", "-l", "jpn+eng", "--psm", "11"],
            capture_output=True, text=True, timeout=35
        )
        return re.sub(r"[ \t]+", " ", p.stdout).strip()
    except Exception as exc:
        return f"[OCR_ERROR] {exc}"

def find_dates(text):
    found = []
    # Explicit Japanese date patterns; do not infer a year from archive capture date.
    for m in re.finditer(r"(?:(20\d{2})\s*[年./-]\s*)?(\d{1,2})\s*[月/.-]\s*(\d{1,2})\s*日?", text):
        year, month, day = m.groups()
        try:
            month, day = int(month), int(day)
            if 1 <= month <= 12 and 1 <= day <= 31:
                found.append(f"{year+'-' if year else ''}{month:02d}-{day:02d}")
        except ValueError:
            pass
    for m in re.finditer(r"(?:(20\d{2})\s*年\s*)?(\d{1,2})\s*日", text):
        year, day = m.groups()
        try:
            day = int(day)
            if 1 <= day <= 31:
                found.append(f"{year+'-' if year else ''}月不明-{day:02d}日")
        except ValueError:
            pass
    return list(dict.fromkeys(found))

if not INDEX.exists():
    raise SystemExit("historical_probe_retry/index.json not found")
records = json.loads(INDEX.read_text(encoding="utf-8"))
rows = []
ocr_lines = []
for rec in records:
    local = rec.get("local_file")
    if not local:
        continue
    path = Path(local)
    if not path.exists():
        path = ROOT / Path(local).name
    if not path.exists():
        continue
    text = ocr(path)
    dates = find_dates(text)
    # classify conservatively; final human review is still needed
    lower = text.lower()
    if any(k in text for k in ["時差開放", "開店", "OPEN", "オープン"]):
        category = "営業ポスター候補"
    elif any(k in text for k in ["新台情報", "新台入替", "増台"]):
        category = "新台・増台告知候補"
    elif any(k in text for k in ["会員募集", "LINE", "禁煙", "駐車場", "お願い", "サービス"]):
        category = "固定案内候補"
    else:
        category = "要確認"
    rows.append({
        "画像ファイル": path.name,
        "分類候補": category,
        "画像内の日付候補": " / ".join(dates),
        "Wayback取得日時": rec.get("recovered_timestamp", ""),
        "元画像URL": rec.get("clean_original_url", rec.get("original_url", "")),
        "確認状況": "要目視確認",
        "OCRテキスト": text.replace("\n", " / ")
    })
    ocr_lines.append(f"===== {path.name} =====\n{text}\n")
with CSV_PATH.open("w", newline="", encoding="utf-8-sig") as f:
    writer = csv.DictWriter(f, fieldnames=["画像ファイル","分類候補","画像内の日付候補","Wayback取得日時","元画像URL","確認状況","OCRテキスト"])
    writer.writeheader()
    writer.writerows(rows)
TXT_PATH.write_text("\n".join(ocr_lines), encoding="utf-8")
print(f"分析対象: {len(rows)}枚")
print(f"日付候補あり: {sum(bool(r['画像内の日付候補']) for r in rows)}枚")
print(f"営業ポスター候補: {sum(r['分類候補']=='営業ポスター候補' for r in rows)}枚")
print(f"CSV: {CSV_PATH}")
print(f"OCR全文: {TXT_PATH}")
