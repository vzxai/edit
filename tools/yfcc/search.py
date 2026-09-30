"""Query the YFCC100M video index (FTS5). Excludes NoDerivs licences (they forbid remixing).

usage: search.py DB "fts query" [limit] [--min 4] [--max 120]
"""
import sqlite3, sys

def search(db, q, limit=40, dmin=4, dmax=180):
    con = sqlite3.connect(db)
    rows = con.execute("""
        SELECT v.photoid, v.duration, v.license, v.taken, v.owner, v.title, v.tags, v.s3key
        FROM vfts JOIN videos v ON v.photoid = vfts.rowid
        WHERE vfts MATCH ? AND v.duration BETWEEN ? AND ? AND v.license NOT LIKE '%NoDerivs%'
        ORDER BY bm25(vfts, 4.0, 1.0, 2.0) LIMIT ?""", (q, dmin, dmax, limit)).fetchall()
    return rows

if __name__ == "__main__":
    db, q = sys.argv[1], sys.argv[2]
    lim = int(sys.argv[3]) if len(sys.argv) > 3 and sys.argv[3].isdigit() else 40
    for pid, dur, lic, taken, owner, title, tags, key in search(db, q, lim):
        lic_s = lic.replace(" License", "").replace("Attribution", "BY").replace("NonCommercial", "NC").replace("ShareAlike", "SA")
        print(f"{pid}\t{dur:5.1f}s\t{lic_s:10s}\t{taken[:10]}\t{title[:50]!s:50s}\t{tags[:90]}")
