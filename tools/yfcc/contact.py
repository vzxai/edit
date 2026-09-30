"""Contact sheets of YFCC100M videos from their per-second keyframes, for picking footage by eye.

usage: contact.py DB OUT.jpg "fts query" [limit]      or      contact.py DB OUT.jpg --ids id1,id2,...
"""
import io, os, sqlite3, sys
from concurrent.futures import ThreadPoolExecutor
import urllib3
from PIL import Image, ImageDraw, ImageFont
sys.path.insert(0, os.path.dirname(__file__))
from search import search

BASE = "https://multimedia-commons.s3.amazonaws.com/"
HTTP = urllib3.ProxyManager(os.environ["HTTPS_PROXY"], maxsize=32, ca_certs="/root/.ccr/ca-bundle.crt") \
    if os.environ.get("HTTPS_PROXY") else urllib3.PoolManager(maxsize=32)
FONT = ImageFont.truetype(os.path.join(os.path.dirname(__file__), "../../brand/fonts/IBMPlexMono-Regular.ttf"), 13)
TW, TH, NF = 200, 112, 6

def keyframe(h, i):
    r = HTTP.request("GET", f"{BASE}data/videos/keyframes/{h[:3]}/{h[3:6]}/{h}-{i:03d}.jpg", timeout=30)
    if r.status != 200: return None
    try: return Image.open(io.BytesIO(r.data)).convert("RGB")
    except Exception: return None

def row(item):
    pid, dur, lic, taken, owner, title, tags, h = item
    n = max(1, int(dur))
    idx = sorted({max(1, min(n, round(n * (k + 0.5) / NF))) for k in range(NF)})
    frames = [keyframe(h, i) for i in idx]
    return item, idx, frames

def sheet(db, out, items):
    with ThreadPoolExecutor(8) as ex:
        rows = list(ex.map(row, items))
    W = 330 + NF * (TW + 4)
    im = Image.new("RGB", (W, len(rows) * (TH + 6) + 4), (18, 18, 20))
    d = ImageDraw.Draw(im)
    for r, (item, idx, frames) in enumerate(rows):
        pid, dur, lic, taken, owner, title, tags, h = item
        y = 4 + r * (TH + 6)
        lic_s = lic.replace(" License", "").replace("Attribution", "BY").replace("NonCommercial", "NC").replace("ShareAlike", "SA")
        d.text((6, y + 2), f"{pid}", fill=(120, 170, 255), font=FONT)
        d.text((6, y + 20), f"{dur:.0f}s {lic_s} {taken[:4]}", fill=(200, 200, 200), font=FONT)
        d.text((6, y + 38), (title or "")[:38], fill=(230, 230, 230), font=FONT)
        d.text((6, y + 56), (tags or "")[:38], fill=(140, 140, 140), font=FONT)
        d.text((6, y + 74), (tags or "")[38:76], fill=(140, 140, 140), font=FONT)
        for k, (i, f) in enumerate(zip(idx, frames)):
            x = 330 + k * (TW + 4)
            if f is None: continue
            f.thumbnail((TW, TH))
            im.paste(f, (x + (TW - f.width) // 2, y + (TH - f.height) // 2))
            d.text((x + 3, y + 2), f"{i}s", fill=(255, 255, 0), font=FONT)
    im.save(out, quality=85)

def batch(db, outdir, tsv, limit=14):
    """many sheets in one process (one connection pool): TSV lines of name<TAB>fts query"""
    for line in open(tsv):
        name, q = line.rstrip("\n").split("\t", 1)
        out = os.path.join(outdir, name + ".jpg")
        if os.path.exists(out): continue
        con = sqlite3.connect(db)
        items = [r[:7] + (con.execute("SELECT hash FROM videos WHERE photoid=?", (r[0],)).fetchone()[0],)
                 for r in search(db, q, limit)]
        sheet(db, out, items)
        print(out, len(items), flush=True)

if __name__ == "__main__":
    if sys.argv[1] == "--batch":
        batch(sys.argv[2], sys.argv[3], sys.argv[4]); sys.exit()
    db, out = sys.argv[1], sys.argv[2]
    con = sqlite3.connect(db)
    if sys.argv[3] == "--ids":
        ids = [int(x) for x in sys.argv[4].split(",")]
        items = []
        for i in ids:
            r = con.execute("SELECT photoid, duration, license, taken, owner, title, tags, hash FROM videos WHERE photoid=?", (i,)).fetchone()
            if r: items.append(r)
    else:
        lim = int(sys.argv[4]) if len(sys.argv) > 4 else 12
        items = [r[:7] + (con.execute("SELECT hash FROM videos WHERE photoid=?", (r[0],)).fetchone()[0],)
                 for r in search(db, sys.argv[3], lim)]
    sheet(db, out, items)
    print(out, len(items))
