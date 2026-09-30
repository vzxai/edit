"""Image effects for the edit: grading, grain, the blue dot, typography."""
import functools
import os

import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

W, H, FPS = 1080, 1920, 30
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FONTS = os.path.join(ROOT, "brand", "fonts")

BLUE = np.array([0, 51, 153], np.float32) / 255          # One World Flag #003399
SIGNAL = np.array([58, 108, 255], np.float32) / 255      # glow around the dot on dark screens
PAPER = (242, 238, 230)                                  # warm white for words
ASH = (160, 168, 180)                                    # muted grey for sources

# ---------------------------------------------------------------- grading

GRADES = {
    # sat: saturation, keep_blue: how much blue survives desaturation, con: contrast,
    # lift/gain: shadows/highlights, tint: RGB multipliers
    "I":   dict(sat=0.28, keep_blue=0.8, con=1.10, lift=0.02, gain=0.96, tint=(0.97, 1.00, 1.05)),
    "II":  dict(sat=0.45, keep_blue=0.6, con=1.22, lift=0.00, gain=0.98, tint=(1.03, 0.98, 0.95)),
    "III": dict(sat=0.15, keep_blue=1.0, con=1.18, lift=0.02, gain=0.95, tint=(0.93, 1.00, 1.08)),
    "IV":  dict(sat=0.65, keep_blue=1.0, con=1.08, lift=0.02, gain=1.00, tint=(1.00, 1.00, 1.02)),
    "V":   dict(sat=1.10, keep_blue=1.0, con=1.10, lift=0.00, gain=1.03, tint=(1.05, 1.00, 0.96)),
    "earth": dict(sat=1.25, keep_blue=0.0, con=1.12, lift=0.00, gain=1.02, tint=(0.98, 1.00, 1.04)),
    "sat": dict(sat=0.95, keep_blue=1.0, con=1.06, lift=0.00, gain=1.00, tint=(1.00, 1.00, 1.00)),
    "raw": None,
}

def grade(img, name):
    """img: HxWx3 uint8 -> uint8"""
    g = GRADES.get(name)
    if g is None:
        return img
    f = img.astype(np.float32) / 255
    luma = f @ np.array([0.2126, 0.7152, 0.0722], np.float32)
    sat = np.full(luma.shape, g["sat"], np.float32)
    if g["keep_blue"] and g["sat"] < 1:
        blueness = np.clip((f[..., 2] - np.maximum(f[..., 0], f[..., 1])) * 4, 0, 1)
        sat = sat + (1 - sat) * blueness * g["keep_blue"]
    f = luma[..., None] + (f - luma[..., None]) * sat[..., None]
    f = (f - 0.5) * g["con"] + 0.5
    f = g["lift"] + f * (g["gain"] - g["lift"])
    f = f * np.array(g["tint"], np.float32)
    return (np.clip(f, 0, 1) * 255).astype(np.uint8)

# ---------------------------------------------------------------- texture

@functools.lru_cache(maxsize=1)
def _grain_bank(n=12, seed=7):
    rng = np.random.default_rng(seed)
    bank = []
    for _ in range(n):
        g = rng.normal(0, 1, (H // 2, W // 2)).astype(np.float32)
        g = cv2.resize(g, (W, H), interpolation=cv2.INTER_LINEAR)
        bank.append(g)
    return bank

@functools.lru_cache(maxsize=1)
def _grain_u8():
    """grain as 8-bit images centred on 128 (so OpenCV's SIMD paths can do the work)"""
    return [cv2.merge([np.clip(g * 42 + 128, 0, 255).astype(np.uint8)] * 3) for g in _grain_bank()]

def grain(frame, amount, i):
    if amount <= 0:
        return frame
    g = _grain_u8()[i % 12]
    a = amount * 255 / 42
    return cv2.addWeighted(frame, 1.0, g, a, -128 * a)

@functools.lru_cache(maxsize=4)
def _vignette(strength):
    y, x = np.mgrid[0:H, 0:W].astype(np.float32)
    d = np.sqrt(((x - W / 2) / (W / 2)) ** 2 + ((y - H / 2) / (H / 2)) ** 2)
    return (1 - strength * np.clip(d - 0.55, 0, 1) ** 1.5).astype(np.float32)[..., None]

@functools.lru_cache(maxsize=4)
def _vignette_u8(strength):
    return cv2.merge([(_vignette(strength)[..., 0] * 255).astype(np.uint8)] * 3)

def vignette(frame, strength=0.55):
    return cv2.multiply(frame, _vignette_u8(strength), scale=1 / 255)

def flash(frame, color, alpha):
    if alpha <= 0:
        return frame
    c = np.array(color, np.float32)
    return (frame.astype(np.float32) * (1 - alpha) + c * alpha).astype(np.uint8)

def chroma_split(frame, px):
    if px <= 0:
        return frame
    out = frame.copy()
    out[..., 0] = np.roll(frame[..., 0], px, axis=1)
    out[..., 2] = np.roll(frame[..., 2], -px, axis=1)
    return out

# ---------------------------------------------------------------- the dot

def _blend_disc(frame, cx, cy, r, color, alpha, blur=0.0):
    """alpha-blend an anti-aliased disc (optionally blurred into a glow) into frame, in place."""
    if r <= 0 or alpha <= 0:
        return
    pad = int(r + 3 * blur + 4)
    x0, y0 = max(0, int(cx - pad)), max(0, int(cy - pad))
    x1, y1 = min(frame.shape[1], int(cx + pad) + 1), min(frame.shape[0], int(cy + pad) + 1)
    if x0 >= x1 or y0 >= y1:
        return
    ss = 4
    mask = np.zeros(((y1 - y0) * ss, (x1 - x0) * ss), np.uint8)
    cv2.circle(mask, (int((cx - x0) * ss), int((cy - y0) * ss)), int(r * ss), 255, -1, lineType=cv2.LINE_AA)
    m = cv2.resize(mask, (x1 - x0, y1 - y0), interpolation=cv2.INTER_AREA).astype(np.float32) / 255
    if blur > 0:
        m = cv2.GaussianBlur(m, (0, 0), blur)
    m = (m * alpha)[..., None]
    region = frame[y0:y1, x0:x1].astype(np.float32)
    frame[y0:y1, x0:x1] = (region * (1 - m) + np.array(color, np.float32) * 255 * m).astype(np.uint8)

def _blend_ring(frame, cx, cy, r, color, alpha, width=2):
    if r <= 0 or alpha <= 0:
        return
    pad = int(r + width + 4)
    x0, y0 = max(0, int(cx - pad)), max(0, int(cy - pad))
    x1, y1 = min(frame.shape[1], int(cx + pad) + 1), min(frame.shape[0], int(cy + pad) + 1)
    if x0 >= x1 or y0 >= y1:
        return
    ss = 4
    mask = np.zeros(((y1 - y0) * ss, (x1 - x0) * ss), np.uint8)
    cv2.circle(mask, (int((cx - x0) * ss), int((cy - y0) * ss)), int(r * ss), 255, int(width * ss), lineType=cv2.LINE_AA)
    m = cv2.resize(mask, (x1 - x0, y1 - y0), interpolation=cv2.INTER_AREA).astype(np.float32) / 255 * alpha
    region = frame[y0:y1, x0:x1].astype(np.float32)
    frame[y0:y1, x0:x1] = (region * (1 - m[..., None]) + np.array(color, np.float32) * 255 * m[..., None]).astype(np.uint8)

def dot(frame, cx, cy, r, alpha=1.0, glow=1.0, ring=False):
    """the blue dot, with a soft light around it (the light matters on dark frames).
    ring=True draws it like the 'you are here' dot on a phone map: a white edge, so it reads on busy pictures."""
    if ring:
        _blend_disc(frame, cx, cy, r * 2.6, SIGNAL, 0.18 * alpha, blur=0)
        _blend_disc(frame, cx, cy, r * 1.32, (1.0, 1.0, 1.0), 0.95 * alpha)
    if glow > 0:
        _blend_disc(frame, cx, cy, r * 2.4, SIGNAL, 0.22 * glow * alpha, blur=r * 0.9)
        _blend_disc(frame, cx, cy, r * 1.35, SIGNAL, 0.35 * glow * alpha, blur=r * 0.25)
    _blend_disc(frame, cx, cy, r, BLUE, alpha)
    # a faint rim of light, like an atmosphere
    _blend_ring(frame, cx, cy, r - 0.5, SIGNAL, 0.35 * alpha * glow, width=max(1.0, r * 0.06))

def ping(frame, cx, cy, r, t, period=1.6, alpha=1.0):
    """'you are here' pulse: rings expanding out of the dot"""
    for k in range(2):
        ph = ((t / period) + k * 0.5) % 1.0
        _blend_ring(frame, cx, cy, r * (1 + 3.2 * ph), SIGNAL, alpha * 0.7 * (1 - ph) ** 1.6, width=max(1.5, r * 0.08))

# ---------------------------------------------------------------- words

@functools.lru_cache(maxsize=16)
def font(name, size):
    files = {
        "serif": "InstrumentSerif-Regular.ttf", "serif-i": "InstrumentSerif-Italic.ttf",
        "mono": "IBMPlexMono-Light.ttf", "mono-r": "IBMPlexMono-Regular.ttf",
        "sans": "Inter-SemiBold.ttf", "sans-b": "Inter-Black.ttf",
    }
    return ImageFont.truetype(os.path.join(FONTS, files[name]), size)

def _wrap(text, fnt, max_w):
    lines = []
    for para in text.split("\n"):
        words, cur = para.split(" "), ""
        for w in words:
            trial = (cur + " " + w).strip()
            if fnt.getlength(trial) <= max_w or not cur:
                cur = trial
            else:
                lines.append(cur); cur = w
        lines.append(cur)
    return lines

@functools.lru_cache(maxsize=256)
def text_layer(text, style="serif", size=64, color=PAPER, max_w=860, align="center", leading=1.18, shadow=True):
    """RGBA numpy image of the laid-out text (cropped to its box)"""
    fnt = font(style, size)
    lines = _wrap(text, fnt, max_w)
    lh = int(size * leading)
    w = int(max(fnt.getlength(l) for l in lines)) + 40
    h = lh * len(lines) + 40
    im = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    for i, l in enumerate(lines):
        lw = fnt.getlength(l)
        x = 20 + ((w - 40 - lw) / 2 if align == "center" else 0)
        d.text((x, 20 + i * lh), l, font=fnt, fill=color + (255,))
    if shadow:
        sh = Image.new("RGBA", im.size, (0, 0, 0, 0))
        sh.putalpha(im.split()[3].filter(ImageFilter.GaussianBlur(size / 7)).point(lambda v: int(v * 0.8)))
        im = Image.alpha_composite(sh, im)
    return np.array(im)

def paste(frame, layer, cx, cy, alpha=1.0, dy=0.0):
    """alpha-composite an RGBA layer centred at (cx, cy)"""
    if alpha <= 0:
        return
    h, w = layer.shape[:2]
    x0, y0 = int(cx - w / 2), int(cy - h / 2 + dy)
    x1, y1 = x0 + w, y0 + h
    fx0, fy0, fx1, fy1 = max(0, x0), max(0, y0), min(frame.shape[1], x1), min(frame.shape[0], y1)
    if fx0 >= fx1 or fy0 >= fy1:
        return
    lay = layer[fy0 - y0:fy1 - y0, fx0 - x0:fx1 - x0].astype(np.float32)
    a = lay[..., 3:4] / 255 * alpha
    region = frame[fy0:fy1, fx0:fx1].astype(np.float32)
    frame[fy0:fy1, fx0:fx1] = (region * (1 - a) + lay[..., :3] * a).astype(np.uint8)

def ease(x):
    x = min(max(x, 0.0), 1.0)
    return x * x * (3 - 2 * x)

def ease_io(x, p=3.0):
    x = min(max(x, 0.0), 1.0)
    return x ** p / (x ** p + (1 - x) ** p)
