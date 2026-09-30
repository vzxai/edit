"""9:16 true-colour window from one or more Sentinel-2 tiles of the same UTM zone (same pass), at native 10 m.

usage: s2_mosaic.py OUT.png LAT LON HEIGHT_KM SCENE_URL [SCENE_URL ...]
"""
import os, sys
os.environ.setdefault("CURL_CA_BUNDLE", "/root/.ccr/ca-bundle.crt")
os.environ.setdefault("GDAL_DISABLE_READDIR_ON_OPEN", "EMPTY_DIR")
os.environ.setdefault("GDAL_HTTP_MERGE_CONSECUTIVE_RANGES", "YES")
import numpy as np
import rasterio
from rasterio.windows import from_bounds
from pyproj import Transformer
from PIL import Image

def main():
    out, lat, lon, hkm = sys.argv[1], float(sys.argv[2]), float(sys.argv[3]), float(sys.argv[4])
    scenes = sys.argv[5:]
    res = 10
    canvas = None
    for url in scenes:
        with rasterio.open(f"/vsicurl/{url}/TCI.tif") as ds:
            if canvas is None:
                cx, cy = Transformer.from_crs("EPSG:4326", ds.crs, always_xy=True).transform(lon, lat)
                H = int(hkm * 1000 / res) // 2 * 2
                W = int(H * 9 / 16) // 2 * 2
                x0, y1 = cx - W * res / 2, cy + H * res / 2
                x1, y0 = x0 + W * res, y1 - H * res
                canvas = np.zeros((H, W, 3), np.uint8)
            bx0, by0 = max(x0, ds.bounds.left), max(y0, ds.bounds.bottom)
            bx1, by1 = min(x1, ds.bounds.right), min(y1, ds.bounds.top)
            if bx0 >= bx1 or by0 >= by1: continue
            a = ds.read(window=from_bounds(bx0, by0, bx1, by1, ds.transform),
                        out_shape=(3, int(round((by1 - by0) / res)), int(round((bx1 - bx0) / res))))
            a = np.transpose(a, (1, 2, 0))
            r0, c0 = int(round((y1 - by1) / res)), int(round((bx0 - x0) / res))
            h, w = min(a.shape[0], H - r0), min(a.shape[1], W - c0)
            a = a[:h, :w]
            m = a.sum(axis=2) > 0
            canvas[r0:r0 + h, c0:c0 + w][m] = a[m]
    Image.fromarray(canvas).save(out)
    print(out, canvas.shape)

if __name__ == "__main__":
    main()
