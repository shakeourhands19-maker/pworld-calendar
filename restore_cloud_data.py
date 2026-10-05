import os
import shutil

SITE_DIR = "site"
DATA_DIR = "data"

os.makedirs(DATA_DIR, exist_ok=True)

history_source = os.path.join(SITE_DIR, "images")
if os.path.isdir(history_source):
    for date in os.listdir(history_source):
        if date == "today":
            continue
        src_dir = os.path.join(history_source, date)
        if not os.path.isdir(src_dir):
            continue
        dst_dir = os.path.join(DATA_DIR, date)
        os.makedirs(dst_dir, exist_ok=True)
        for filename in os.listdir(src_dir):
            src = os.path.join(src_dir, filename)
            dst = os.path.join(dst_dir, filename)
            if os.path.isfile(src):
                shutil.copy2(src, dst)

layout_source = os.path.join(SITE_DIR, "layouts")
layout_dest = os.path.join(DATA_DIR, "layouts")
if os.path.isdir(layout_source):
    os.makedirs(layout_dest, exist_ok=True)
    for filename in os.listdir(layout_source):
        src = os.path.join(layout_source, filename)
        dst = os.path.join(layout_dest, filename)
        if os.path.isfile(src):
            shutil.copy2(src, dst)

layout_index_source = os.path.join(SITE_DIR, "layout_index.json")
layout_index_dest = os.path.join(DATA_DIR, "layout_index.json")
if os.path.isfile(layout_index_source):
    shutil.copy2(layout_index_source, layout_index_dest)

print("GitHub Pagesに保存していた過去データを復元しました。")


# みんレポ過去データを復元
MINREPO_SOURCE = os.path.join(SITE_DIR, "minrepo_data")
MINREPO_DEST = "minrepo_data"
if os.path.isdir(MINREPO_SOURCE):
    os.makedirs(MINREPO_DEST, exist_ok=True)
    for filename in os.listdir(MINREPO_SOURCE):
        src = os.path.join(MINREPO_SOURCE, filename)
        dst = os.path.join(MINREPO_DEST, filename)
        if os.path.isfile(src):
            shutil.copy2(src, dst)
    print("みんレポ過去データを復元しました。")
