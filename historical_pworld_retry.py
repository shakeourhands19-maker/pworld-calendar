import json, os, re, time
from pathlib import Path
from urllib.parse import urlparse
import requests

INPUT=Path("historical_probe/index.json")
OUT=Path("historical_probe_retry"); IMG=OUT/"images"; IMG.mkdir(parents=True,exist_ok=True)
CDX="https://web.archive.org/cdx/search/cdx"
START_YEAR=os.getenv("START_YEAR","2024"); END_YEAR=os.getenv("END_YEAR","2026")
s=requests.Session(); s.headers.update({"User-Agent":"Mozilla/5.0 Chrome/154.0 Safari/537.36"})

def cdx(url):
    p={"url":url,"output":"json","filter":"statuscode:200","from":START_YEAR,"to":END_YEAR,"fl":"timestamp,original,mimetype,statuscode,digest","collapse":"digest","limit":1000}
    r=s.get(CDX,params=p,timeout=60); r.raise_for_status(); rows=r.json()
    return [dict(zip(rows[0],x)) for x in rows[1:]] if rows else []

def au(ts,url): return f"https://web.archive.org/web/{ts}id_/{url}"
def clean(u): return re.sub(r"\?\d+$","",u or "")
def fname(i,u):
    n=Path(urlparse(u).path).name or "image.jpg"
    return f"{i:04d}_{re.sub(r'[^0-9A-Za-z._-]+','_',n)}"

records=json.loads(INPUT.read_text(encoding="utf-8"))
ok=fail=0
for i,rec in enumerate(records,1):
    u=clean(rec["original_url"]); print(f"[{i}/{len(records)}] {u}")
    try: caps=cdx(u)
    except Exception as e: rec["retry_error"]=str(e); fail+=1; continue
    got=False
    print(f"  保存候補: {len(caps)}件")
    for cap in caps:
        try:
            r=s.get(au(cap["timestamp"],u),timeout=60)
            if r.status_code!=200 or not r.headers.get("content-type","").startswith("image/"): continue
            p=IMG/fname(i,u); p.write_bytes(r.content)
            rec.update({"clean_original_url":u,"recovered_timestamp":cap["timestamp"],"recovered_url":au(cap["timestamp"],u),"local_file":str(p),"recovered_size":len(r.content)})
            ok+=1; got=True; print(f"  OK: {cap['timestamp']} / {len(r.content):,} bytes"); break
        except Exception: pass
    if not got: rec["recovery_failed"]=True; fail+=1; print("  NG")
    time.sleep(.15)
(OUT/"index.json").write_text(json.dumps(records,ensure_ascii=False,indent=2),encoding="utf-8")
(OUT/"summary.json").write_text(json.dumps({"input_images":len(records),"recovered":ok,"failed":fail,"start_year":START_YEAR,"end_year":END_YEAR},ensure_ascii=False,indent=2),encoding="utf-8")
print(f"完了: {len(records)}件中 {ok}件取得 / {fail}件失敗")