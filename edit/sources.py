"""Frame sources: found footage (decoded with ffmpeg), satellite stills, GOES sequences."""
import functools
import glob
import json
import os
import subprocess

import cv2
import numpy as np
from PIL import Image

from fx import FPS, H, W

SCRATCH = os.environ.get("EDIT_SCRATCH", "/tmp/claude-0/-home-user-edit/97209c75-c389-57a0-a075-f298b8515df7/scratchpad")
MEDIA = os.environ.get("EDIT_MEDIA", os.path.join(SCRATCH, "media"))
SAT = os.environ.get("EDIT_SAT", os.path.join(SCRATCH, "sat"))
Image.MAX_IMAGE_PIXELS = None

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
NEWS = os.environ.get("EDIT_NEWS", os.path.join(ROOT, "footage", "news"))

def yfcc(pid):
    return os.path.join(MEDIA, "yfcc", f"{pid}.mp4")

def news(nid):
    """footage fetched by tools/fetch_wanted.py (see edit/wanted.json)"""
    return os.path.join(NEWS, f"{nid}.mp4")

def news_meta(nid):
    p = os.path.join(NEWS, f"{nid}.json")
    return json.load(open(p)) if os.path.exists(p) else {}

@functools.lru_cache(maxsize=512)
def probe(path):
    out = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries",
                          "stream=width,height:stream_side_data=rotation:stream_tags=rotate:format=duration",
                          "-of", "json", path], capture_output=True, text=True).stdout
    d = json.loads(out)
    s = d["streams"][0]
    w, h = s["width"], s["height"]
    rot = int(s.get("tags", {}).get("rotate", 0))
    for sd in s.get("side_data_list", []) or []:
        if "rotation" in sd:
            rot = int(sd["rotation"])
    if abs(rot) % 180 == 90:
        w, h = h, w
    return w, h, float(d["format"].get("duration", 0))

def video_frames(path, t_in, n, speed=1.0):
    """n RGB frames at FPS starting at t_in (holds the last frame if the clip runs out)"""
    w, h, dur = probe(path)
    t_in = max(0.0, min(t_in, max(0.0, dur - 0.2)))
    vf = f"setpts=PTS/{speed},fps={FPS}" if speed != 1.0 else f"fps={FPS}"
    cmd = ["ffmpeg", "-v", "error", "-ss", f"{t_in:.3f}", "-i", path, "-t", f"{n / FPS * speed + 0.5:.3f}",
           "-vf", vf, "-f", "rawvideo", "-pix_fmt", "rgb24", "-"]
    p = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)
    size = w * h * 3
    last = np.zeros((h, w, 3), np.uint8)
    for _ in range(n):
        buf = p.stdout.read(size)
        if len(buf) == size:
            last = np.frombuffer(buf, np.uint8).reshape(h, w, 3)
        yield last
    p.stdout.close()
    p.kill()
    p.wait()

@functools.lru_cache(maxsize=8)
def still(path):
    return np.array(Image.open(path).convert("RGB"))

@functools.lru_cache(maxsize=2)
def goes_day(size=2160):
    files = sorted(glob.glob(os.path.join(SAT, "goes_day", "goes19_*.png")))
    return files

@functools.lru_cache(maxsize=96)
def goes_frame(path):
    return np.array(Image.open(path).convert("RGB"))

def goes_at(pos, files, size=None):
    """blend neighbouring GOES frames for a fractional index (smooth time-lapse), optionally resized first"""
    pos = min(max(pos, 0), len(files) - 1)
    i = int(pos)
    j = min(i + 1, len(files) - 1)
    a = pos - i
    def get(k):
        f = goes_frame(files[k])
        return cv2.resize(f, (size, size), interpolation=cv2.INTER_AREA) if size else f
    f0 = get(i)
    if a < 1e-3 or i == j:
        return f0
    return cv2.addWeighted(f0, 1 - a, get(j), a, 0)

# GOES-19 ABI full-disk fixed grid (2 km): x/y scan angles in radians
GOES_LON0, GOES_H = -75.2, 35786023.0
GOES_X0, GOES_DX = -0.151844, 5.6e-05

def goes_pixel(lat, lon, n=5424):
    """column/row of a lat/lon on the n x n full-disk image"""
    from pyproj import Proj
    p = Proj(proj="geos", h=GOES_H, lon_0=GOES_LON0, sweep="x", a=6378137.0, b=6356752.31414)
    x, y = p(lon, lat)
    xr, yr = x / GOES_H, y / GOES_H
    col = (xr - GOES_X0) / GOES_DX
    row = (-GOES_X0 - yr) / GOES_DX
    return col * n / 5424, row * n / 5424

def crop_zoom(img, cx, cy, vis_h, out_w=W, out_h=H, nearest_below=1.0):
    """crop a out_w:out_h box of height vis_h (source px) centred at (cx, cy) and resize to out size.
    When a source pixel becomes bigger than `nearest_below` output pixels, keep pixels square and hard."""
    vis_w = vis_h * out_w / out_h
    x0, y0 = cx - vis_w / 2, cy - vis_h / 2
    scale = out_h / vis_h
    M = np.array([[scale, 0, -x0 * scale], [0, scale, -y0 * scale]], np.float32)
    interp = cv2.INTER_NEAREST if scale > nearest_below * 2.5 else (cv2.INTER_AREA if scale < 1 else cv2.INTER_CUBIC)
    if scale < 1:
        # pre-shrink for quality, then warp
        k = max(1, int(1 / scale))
        if k > 1:
            small = cv2.resize(img, (img.shape[1] // k, img.shape[0] // k), interpolation=cv2.INTER_AREA)
            M2 = M.copy(); M2[:, :2] *= k
            return cv2.warpAffine(small, M2, (out_w, out_h), flags=cv2.INTER_LINEAR, borderValue=(0, 0, 0))
    return cv2.warpAffine(img, M, (out_w, out_h), flags=interp, borderValue=(0, 0, 0))
