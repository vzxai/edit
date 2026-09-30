"""Stream the whole YFCC100M SQLite dump through the C scanner in parallel byte ranges."""
import os, subprocess, sys, time
from concurrent.futures import ThreadPoolExecutor

URL = "https://multimedia-commons.s3.amazonaws.com/tools/etc/yfcc100m_dataset.sql"
NPAGES, PS = 64105496, 1024
OUT = sys.argv[1]
SCAN = sys.argv[2] if len(sys.argv) > 2 else "/tmp/yfcc_scan"
NSEG, WORKERS = 128, int(os.environ.get("WORKERS", 8))
per = -(-NPAGES // NSEG)

def run(k):
    start = 1 + k * per
    end = min(NPAGES, start + per - 1)
    expect = end - start + 1
    out = f"{OUT}/seg_{k:03d}.tsv"
    if os.path.exists(out + ".ok"):
        return k, "cached"
    for attempt in range(4):
        cmd = f"curl -sS --retry 5 -r {(start-1)*PS}-{end*PS-1} '{URL}' | {SCAN} {start} > {out} 2> {out}.err"
        subprocess.run(cmd, shell=True)
        err = open(out + ".err").read()
        if f"pages={expect} " in err:
            open(out + ".ok", "w").write(err)
            return k, err.strip()
        time.sleep(2 * (attempt + 1))
    return k, "FAILED " + err.strip()

t0 = time.time()
with ThreadPoolExecutor(WORKERS) as ex:
    for i, (k, msg) in enumerate(ex.map(run, range(NSEG))):
        print(f"[{time.time()-t0:7.0f}s] seg {k:03d} {msg}", flush=True)
print("ALL DONE", time.time() - t0, flush=True)
