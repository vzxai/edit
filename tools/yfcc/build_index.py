"""Merge scanner output into a searchable SQLite (FTS5) index of YFCC100M videos.

Resolves '#UNRES' rows (overflow chains the streaming scan could not follow)
with HTTP range reads, decodes Flickr's URL-encoded text, and derives each
video's S3 key: md5(downloadurl) printed as unpadded hex bytes.
"""
import glob, hashlib, os, sqlite3, struct, sys, urllib.parse, urllib.request
from concurrent.futures import ThreadPoolExecutor
import urllib3

URL = "https://multimedia-commons.s3.amazonaws.com/tools/etc/yfcc100m_dataset.sql"
LEN_URL = "https://multimedia-commons.s3.amazonaws.com/data/videos/metadata/video_length.txt"
PS = U = 1024
COLS = ("uid unickname datetaken dateuploaded capturedevice title description usertags machinetags "
        "longitude latitude accuracy pageurl downloadurl licensename licenseurl serverid farmid "
        "secret secretoriginal ext marker").split()

# one pooled client: building a fresh SSL context per request (urllib's default) is CPU-bound
HTTP = urllib3.ProxyManager(os.environ["HTTPS_PROXY"], maxsize=64, ca_certs=os.environ.get("SSL_CERT_FILE", "/root/.ccr/ca-bundle.crt")) \
    if os.environ.get("HTTPS_PROXY") else urllib3.PoolManager(maxsize=64)

def rng(a, b):
    for attempt in range(5):
        try:
            r = HTTP.request("GET", URL, headers={"Range": f"bytes={a}-{b}"}, timeout=60, retries=False)
            if r.status in (200, 206): return r.data
        except Exception:
            if attempt == 4: raise
    raise IOError(f"range {a}-{b} failed")

def varint(b, i):
    v = 0
    for k in range(9):
        c = b[i + k]
        if k == 8: return (v << 8) | c, i + 9
        v = (v << 7) | (c & 0x7F)
        if c < 0x80: return v, i + k + 1

def decode_record(rec):
    hs, j = varint(rec, 0); types = []
    while j < hs:
        t, j = varint(rec, j); types.append(t)
    vals, k = [], hs
    for t in types:
        if t >= 13 and t % 2: L = (t - 13) // 2; vals.append(rec[k:k + L].decode("utf8", "replace")); k += L
        elif t >= 12: L = (t - 12) // 2; vals.append(""); k += L
        elif 1 <= t <= 6:
            L = {1: 1, 2: 2, 3: 3, 4: 4, 5: 6, 6: 8}[t]; vals.append(str(int.from_bytes(rec[k:k + L], "big", signed=True))); k += L
        elif t == 7: vals.append(str(struct.unpack(">d", rec[k:k + 8])[0])); k += 8
        elif t == 8: vals.append("0")
        elif t == 9: vals.append("1")
        else: vals.append("")
    return vals[1:]

def resolve(line):
    _, rowid, P, nxt, used, hexbuf = line.rstrip("\n").split("\t")
    P, nxt = int(P), int(nxt)
    buf = bytearray(bytes.fromhex(hexbuf))
    while len(buf) < P and nxt:
        pg = rng((nxt - 1) * PS, nxt * PS - 1)
        nxt = struct.unpack(">I", pg[:4])[0]
        buf += pg[4:4 + min(U - 4, P - len(buf))]
    return [rowid] + decode_record(bytes(buf))

def yfcc_hash(downloadurl):
    return "".join("%x" % b for b in hashlib.md5(downloadurl.encode()).digest())

def dec(s):
    return urllib.parse.unquote_plus(s) if s and s != "\\TRUNC" else ""

def main(segdir, dbpath):
    rows, unres = [], []
    for f in sorted(glob.glob(f"{segdir}/seg_*.tsv")):
        for line in open(f, encoding="utf8", errors="replace"):
            if line.startswith("#UNRES"): unres.append(line)
            else:
                parts = line.rstrip("\n").split("\t")
                if len(parts) == 23: rows.append(parts)
    print("rows", len(rows), "unresolved", len(unres), flush=True)
    with ThreadPoolExecutor(48) as ex:
        for r in ex.map(resolve, unres):
            if len(r) == 23: rows.append(r)
    lengths = {}
    for line in urllib.request.urlopen(LEN_URL, timeout=120).read().decode().splitlines():
        name, _, dur = line.partition(" ")
        h = name.replace(".mp4", "")
        try:
            hh, mm, ss = dur.strip().split(":"); lengths[h] = int(hh) * 3600 + int(mm) * 60 + float(ss)
        except ValueError: pass
    if os.path.exists(dbpath): os.remove(dbpath)
    db = sqlite3.connect(dbpath)
    db.execute("""CREATE TABLE videos (photoid INTEGER PRIMARY KEY, uid TEXT, owner TEXT, taken TEXT,
        device TEXT, title TEXT, description TEXT, tags TEXT, lon TEXT, lat TEXT, pageurl TEXT,
        license TEXT, licenseurl TEXT, hash TEXT, s3key TEXT, duration REAL)""")
    db.execute("CREATE VIRTUAL TABLE vfts USING fts5(title, description, tags, content='videos', content_rowid='photoid')")
    out, seen = [], set()
    for r in rows:
        d = dict(zip(["photoid"] + COLS, r))
        dl = d["downloadurl"]
        if not dl or dl == "\\TRUNC" or "/play/orig/" not in dl: continue
        pid = int(d["photoid"])
        if pid in seen: continue
        seen.add(pid)
        h = yfcc_hash(dl)
        out.append((pid, d["uid"], dec(d["unickname"]), d["datetaken"], dec(d["capturedevice"]), dec(d["title"]),
                    dec(d["description"]), dec(d["usertags"]).replace(",", ", "), d["longitude"], d["latitude"],
                    d["pageurl"], dec(d["licensename"]), d["licenseurl"], h,
                    f"data/videos/mp4/{h[:3]}/{h[3:6]}/{h}.mp4", lengths.get(h)))
    db.executemany("INSERT INTO videos VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)", out)
    db.execute("INSERT INTO vfts(rowid, title, description, tags) SELECT photoid, title, description, tags FROM videos")
    db.commit()
    n_av = db.execute("SELECT count(*) FROM videos WHERE duration IS NOT NULL").fetchone()[0]
    print("indexed", len(out), "with media on S3:", n_av)

if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
