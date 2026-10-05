import json
import os
import re
import time
from pathlib import Path
from urllib.parse import urlparse
import requests

INPUT=Path("historical_probe/index.json")
OUT=Path("historical_probe_retry")
IMG=OUT/"images"
IMG.mkdir(parents=True,exist_ok=True)

CDX="https://web.archive.org/cdx/search/cdx"
START_YEAR=os.getenv("START_YEAR","2024")
END_YEAR=os.getenv("END_YEAR","2026")
MAX_IMAGES=int(os.getenv("MAX_IMAGES","10"))
MAX_CANDIDATES=int(os.getenv("MAX_CANDIDATES","3"))

s=requests.Session()
s.headers.update({"User-Agent":"Mozilla/5.0 Chrome/154.0 Safari/537.36"})

def cdx(url):
    p={
        "url":url,
        "output":"json",
        "filter":"statuscode:200",
        "from":START_YEAR,
        "to":END_YEAR,
        "fl":"timestamp,original,mimetype,statuscode,digest",
        "collapse":"digest",
        "limit":20
    }
    r=s.get(CDX,params=p,timeout=20)
    r.raise_for_status()
    rows=r.json()
    return [dict(zip(rows[0],x)) for x in rows[1:]] if rows else []

def au(ts,url):
    return f"https://web.archive.org/web/{ts}id_/{url}"

def clean(u):
    return re.sub(r"\?\d+$","",u or "")

def fname(i,u):
    n=Path(urlparse(u).path).name or "image.jpg"
    return f"{i:04d}_{re.sub(r'[^0-9A-Za-z._-]+','_',n)}"

records=json.loads(INPUT.read_text(encoding="utf-8"))
records=records[:MAX_IMAGES]

ok=fail=0
print("="*60)
print(f"画像URL個別再発掘テスト: {len(records)}枚")
print(f"候補確認: 最大{MAX_CANDIDATES}件/画像")
print("="*60)

for i,rec in enumerate(records,1):
    u=clean(rec["original_url"])
    print(f"[{i}/{len(records)}] {u}",flush=True)

    try:
        caps=cdx(u)[:MAX_CANDIDATES]
        print(f"  保存候補: {len(caps)}件",flush=True)
    except Exception as e:
        rec["retry_error"]=str(e)
        fail+=1
        print(f"  CDX失敗: {e}",flush=True)
        continue

    got=False
    for cap in caps:
        try:
            r=s.get(au(cap["timestamp"],u),timeout=15)
            ct=r.headers.get("content-type","")
            if r.status_code!=200 or not ct.startswith("image/"):
                continue
            p=IMG/fname(i,u)
            p.write_bytes(r.content)
            rec.update({
                "clean_original_url":u,
                "recovered_timestamp":cap["timestamp"],
                "recovered_url":au(cap["timestamp"],u),
                "local_file":str(p),
                "recovered_size":len(r.content)
            })
            ok+=1
            got=True
            print(f"  OK: {cap['timestamp']} / {len(r.content):,} bytes",flush=True)
            break
        except Exception:
            continue

    if not got:
        rec["recovery_failed"]=True
        fail+=1
        print("  NG",flush=True)

    time.sleep(.1)

(OUT/"index.json").write_text(
    json.dumps(records,ensure_ascii=False,indent=2),
    encoding="utf-8"
)
(OUT/"summary.json").write_text(
    json.dumps({
        "input_images":len(records),
        "recovered":ok,
        "failed":fail,
        "start_year":START_YEAR,
        "end_year":END_YEAR,
        "max_candidates":MAX_CANDIDATES
    },ensure_ascii=False,indent=2),
    encoding="utf-8"
)

print("="*60)
print(f"完了: {len(records)}件中 {ok}件取得 / {fail}件失敗")
