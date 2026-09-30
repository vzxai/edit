"""Grab single frames at given times (for checking looks without rendering everything)."""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from PIL import Image
import render

def grab(times, outdir):
    os.makedirs(outdir, exist_ok=True)
    for t in times:
        for abs_t, f in render.frames(t, t + 1.0 / render.FPS + 1e-6):
            Image.fromarray(f).resize((540, 960)).save(os.path.join(outdir, f"frame_{t:06.2f}.jpg"), quality=88)
            break

if __name__ == "__main__":
    grab([float(x) for x in sys.argv[2:]], sys.argv[1])
