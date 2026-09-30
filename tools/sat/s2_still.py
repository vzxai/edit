"""Cut a 9:16 true-colour still, centred on a place, out of a Sentinel-2 L2A tile (public COGs on AWS).

usage: s2_still.py SCENE_URL LAT LON OUT.png [--max-km 30] [--overview 0]
SCENE_URL is the scene folder, e.g. https://sentinel-cogs.s3.us-west-2.amazonaws.com/sentinel-s2-l2a-cogs/18/S/UJ/2026/9/S2C_18SUJ_20260916_0_L2A
The window is the largest 9:16 box centred on the point that stays inside the tile (capped at --max-km tall).
"""
import os, sys
os.environ.setdefault("CURL_CA_BUNDLE", "/root/.ccr/ca-bundle.crt")
os.environ.setdefault("GDAL_DISABLE_READDIR_ON_OPEN", "EMPTY_DIR")
os.environ.setdefault("GDAL_HTTP_MERGE_CONSECUTIVE_RANGES", "YES")
import numpy as np
import rasterio
from rasterio.windows import Window
from pyproj import Transformer
from PIL import Image

def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    opts = dict(zip(sys.argv[1::1], sys.argv[2::1]))
    url, lat, lon, out = args[0], float(args[1]), float(args[2]), args[3]
    max_km = float(opts.get("--max-km", 30))
    with rasterio.open(f"/vsicurl/{url}/TCI.tif") as ds:
        x, y = Transformer.from_crs("EPSG:4326", ds.crs, always_xy=True).transform(lon, lat)
        col, row = ~ds.transform * (x, y)
        res = ds.res[0]
        half_h = min(row, ds.height - row, (col / (9 / 16)), (ds.width - col) / (9 / 16), max_km * 500 / res)
        half_w = half_h * 9 / 16
        win = Window(col - half_w, row - half_h, 2 * half_w, 2 * half_h)
        rgb = ds.read(window=win)            # (3, H, W) uint8, already stretched by ESA
    img = np.transpose(rgb, (1, 2, 0))
    Image.fromarray(img).save(out)
    print(out, img.shape, f"{2*half_h*res/1000:.1f} km tall", f"centre px ({half_w:.0f},{half_h:.0f})")

if __name__ == "__main__":
    main()
