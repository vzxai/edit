"""Symbol files for the movement, built on the One World Flag (Thomas Mandl, 2016; public domain):
a blue dot (#003399) centred on a transparent 2:3 field.

Outputs SVG + transparent PNGs: the flag, the bare dot, and a luminous 'signal' variant for dark screens.
"""
import os
from PIL import Image, ImageDraw, ImageFilter

OUT = os.path.join(os.path.dirname(__file__), "symbol")
os.makedirs(OUT, exist_ok=True)
BLUE = (0, 51, 153)           # #003399 — the One World Flag blue
SIGNAL = (58, 108, 255)       # lifted blue used only for glow/halo on black
DOT = 2 / 5                   # dot diameter as a fraction of flag height

def svg_flag(path, w=900, h=600):
    r = h * DOT / 2
    open(path, "w").write(
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" viewBox="0 0 {w} {h}">'
        f'<circle cx="{w/2}" cy="{h/2}" r="{r:g}" fill="#003399"/></svg>\n')

def svg_dot(path, s=600):
    open(path, "w").write(
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{s}" height="{s}" viewBox="0 0 {s} {s}">'
        f'<circle cx="{s/2}" cy="{s/2}" r="{s/2}" fill="#003399"/></svg>\n')

def disc(size, diameter, color, ss=4):
    """anti-aliased disc on a transparent canvas"""
    W, H = size[0] * ss, size[1] * ss
    im = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    r = diameter * ss / 2
    cx, cy = W / 2, H / 2
    d.ellipse([cx - r, cy - r, cx + r, cy + r], fill=color + (255,))
    return im.resize(size, Image.LANCZOS)

def signal(size, diameter):
    """the dot with a soft light around it, for black backgrounds"""
    base = Image.new("RGBA", size, (0, 0, 0, 0))
    for mult, alpha, blur in [(3.2, 40, diameter * 0.9), (1.8, 90, diameter * 0.35), (1.15, 160, diameter * 0.08)]:
        halo = disc(size, diameter * mult * 0.5, SIGNAL)
        a = halo.split()[3].point(lambda v: v * alpha // 255)
        halo.putalpha(a)
        base = Image.alpha_composite(base, halo.filter(ImageFilter.GaussianBlur(blur)))
    return Image.alpha_composite(base, disc(size, diameter, BLUE))

svg_flag(f"{OUT}/one-world-flag.svg")
svg_dot(f"{OUT}/blue-dot.svg")
for h in (600, 1200, 2400):
    disc((h * 3 // 2, h), h * DOT, BLUE).save(f"{OUT}/one-world-flag-{h * 3 // 2}x{h}.png")
for s in (256, 512, 1024, 2048):
    disc((s, s), s, BLUE).save(f"{OUT}/blue-dot-{s}.png")
signal((1024, 1024), 300).save(f"{OUT}/blue-dot-signal-1024.png")
# avatars: dot on black, dot on white (for profile pictures)
for bg, name in [((5, 7, 13), "night"), ((244, 241, 234), "paper")]:
    im = Image.new("RGBA", (1080, 1080), bg + (255,))
    im = Image.alpha_composite(im, signal((1080, 1080), 380) if name == "night" else disc((1080, 1080), 380, BLUE))
    im.convert("RGB").save(f"{OUT}/avatar-{name}-1080.png")
print(sorted(os.listdir(OUT)))
