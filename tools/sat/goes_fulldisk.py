"""True-colour full-disk Earth frames from NOAA GOES-19 (ABI L2 MCMIPF, 2 km, public on AWS).

usage: goes_fulldisk.py OUTDIR YEAR DOY HH:MM [HH:MM ...]   (UTC; nearest 10-minute scan is used)
Writes OUTDIR/goes19_<YYYYDDD>_<HHMM>.png (2160x2160) and, with --master, the full 5424x5424 frame.
"""
import datetime, os, re, subprocess, sys, tempfile, urllib.request
import numpy as np
import h5py
from PIL import Image

BUCKET = "https://noaa-goes19.s3.amazonaws.com"

def list_keys(prefix):
    xml = urllib.request.urlopen(f"{BUCKET}/?list-type=2&prefix={prefix}", timeout=60).read().decode()
    return re.findall(r"<Key>([^<]+)</Key>", xml)

def fetch(key, dst, streams=8):
    size = int(re.search(r"<Size>(\d+)</Size>", urllib.request.urlopen(f"{BUCKET}/?list-type=2&prefix={key}", timeout=60).read().decode()).group(1))
    step = -(-size // streams)
    parts = []
    procs = []
    for i in range(streams):
        a, b = i * step, min(size, (i + 1) * step) - 1
        part = f"{dst}.part{i}"
        parts.append(part)
        procs.append(subprocess.Popen(["curl", "-sS", "--retry", "5", "--max-time", "300", "-r", f"{a}-{b}", "-o", part, f"{BUCKET}/{key}"]))
    for p in procs: p.wait()
    with open(dst, "wb") as out:
        for part in parts:
            out.write(open(part, "rb").read()); os.remove(part)
    assert os.path.getsize(dst) == size, "short download"

def band(h, name):
    v = h[name]
    a = v[:].astype(np.float32)
    fill = v.attrs.get("_FillValue")
    if fill is not None: a[v[:] == fill[0]] = np.nan
    a = a * v.attrs.get("scale_factor", [1.0])[0] + v.attrs.get("add_offset", [0.0])[0]
    return a

def true_colour(path):
    with h5py.File(path, "r") as h:
        B, R, V = band(h, "CMI_C01"), band(h, "CMI_C02"), band(h, "CMI_C03")
    R, B, V = [np.clip(np.nan_to_num(x, nan=0.0), 0, 1) for x in (R, B, V)]
    G = np.clip(0.45 * R + 0.10 * V + 0.45 * B, 0, 1)        # CIMSS 'natural' green
    rgb = np.dstack([R, G, B])
    rgb = np.power(rgb, 1 / 2.2)                              # gamma
    # gentle S-curve for contrast
    rgb = np.clip(rgb * 1.08 - 0.02, 0, 1)
    return (rgb * 255).astype(np.uint8)

def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    master = "--master" in sys.argv
    out, year, doy, times = args[0], int(args[1]), int(args[2]), args[3:]
    os.makedirs(out, exist_ok=True)
    tmp = tempfile.mkdtemp(dir=out)
    for t in times:
        hh, mm = map(int, t.split(":"))
        keys = list_keys(f"ABI-L2-MCMIPF/{year}/{doy:03d}/{hh:02d}/")
        if not keys: print("no data", t); continue
        # scan start time is sYYYYDDDHHMMSSs
        def start(k): s = re.search(r"_s(\d{13})", k).group(1); return int(s[9:11])
        key = min(keys, key=lambda k: abs(start(k) - mm))
        name = f"goes19_{year}{doy:03d}_{hh:02d}{start(key):02d}"
        dst = os.path.join(out, name + ".png")
        if os.path.exists(dst): print("have", name); continue
        nc = os.path.join(tmp, "f.nc")
        fetch(key, nc)
        rgb = true_colour(nc)
        os.remove(nc)
        im = Image.fromarray(rgb)
        if master: im.save(os.path.join(out, name + "_master.png"))
        im.resize((2160, 2160), Image.LANCZOS).save(dst)
        print("wrote", dst, flush=True)
    os.rmdir(tmp)

if __name__ == "__main__":
    main()
