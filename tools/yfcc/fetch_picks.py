"""Download picked YFCC100M videos and write their attribution (CC licences require it).

usage: fetch_picks.py DB PICKS.tsv OUTDIR CREDITS.tsv
"""
import csv, os, sqlite3, subprocess, sys
from concurrent.futures import ThreadPoolExecutor

BASE = "https://multimedia-commons.s3.amazonaws.com/"

def main(db, picks, outdir, credits):
    os.makedirs(outdir, exist_ok=True)
    con = sqlite3.connect(db)
    ids = []
    for line in open(picks):
        if line.startswith("#") or not line.strip(): continue
        ids.append(int(line.split("\t")[0]))
    rows = []
    for pid in dict.fromkeys(ids):
        r = con.execute("SELECT photoid, owner, uid, title, license, licenseurl, pageurl, s3key, duration, taken FROM videos WHERE photoid=?", (pid,)).fetchone()
        if r: rows.append(r)
    def get(r):
        dst = os.path.join(outdir, f"{r[0]}.mp4")
        if not os.path.exists(dst) or os.path.getsize(dst) == 0:
            subprocess.run(["curl", "-sS", "--retry", "5", "-o", dst, BASE + r[7]], check=False)
        return r[0], os.path.exists(dst) and os.path.getsize(dst) > 0
    with ThreadPoolExecutor(6) as ex:
        ok = dict(ex.map(get, rows))
    with open(credits, "w", newline="") as f:
        w = csv.writer(f, delimiter="\t")
        w.writerow(["photoid", "author", "title", "license", "license_url", "source", "taken"])
        for r in rows:
            if ok.get(r[0]): w.writerow([r[0], r[1], r[3], r[4], r[5], r[6], r[9][:10]])
    print(f"downloaded {sum(ok.values())}/{len(rows)}")

if __name__ == "__main__":
    main(*sys.argv[1:5])
