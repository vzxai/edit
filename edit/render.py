"""Render the edit: timeline.py -> 1080x1920, 30 fps, H.264 + AAC.

usage: python3 edit/render.py OUT.mp4 [--from SEC] [--to SEC] [--song SONG.mp3] [--preview]
"""
import argparse
import math
import os
import subprocess
import sys

import cv2
import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import fx
import sources as src
import timeline as TL
from fx import FPS, H, W

# ------------------------------------------------------------------ helpers

def canvas():
    return np.zeros((H, W, 3), np.uint8)

def place_window(img, width=1080, cy=880, zoom=1.0, focus=(0.5, 0.5)):
    """found footage floats in the dark, full width, slightly above centre"""
    h, w = img.shape[:2]
    cw, ch = w / zoom, h / zoom
    x0 = (w - cw) * focus[0]
    y0 = (h - ch) * focus[1]
    crop = img[int(y0):int(y0 + ch), int(x0):int(x0 + cw)]
    th = int(round(width * crop.shape[0] / crop.shape[1]))
    th = min(th, H)
    out = cv2.resize(crop, (width, th), interpolation=cv2.INTER_CUBIC)
    c = canvas()
    y = int(cy - th / 2)
    y = max(0, min(H - th, y))
    x = (W - width) // 2
    c[y:y + th, x:x + width] = out
    return c, (x, y, width, th)

def place_fill(img, zoom=1.0, focus=(0.5, 0.5)):
    h, w = img.shape[:2]
    scale = max(W / w, H / h) * zoom
    vis_w, vis_h = W / scale, H / scale
    x0 = (w - vis_w) * focus[0]
    y0 = (h - vis_h) * focus[1]
    M = np.array([[scale, 0, -x0 * scale], [0, scale, -y0 * scale]], np.float32)
    return cv2.warpAffine(img, M, (W, H), flags=cv2.INTER_CUBIC), (0, 0, W, H)

def shade(frame, y0, y1, strength=0.6, feather=120):
    """darken a horizontal band (with soft edges) so words can sit on busy pictures"""
    ys = np.arange(H, dtype=np.float32)
    m = np.clip(np.minimum(ys - (y0 - feather), (y1 + feather) - ys) / feather, 0, 1) * strength
    return (frame.astype(np.float32) * (1 - m[:, None, None])).astype(np.uint8)

def caption(frame, text, y, size=26, alpha=1.0, style="mono", color=fx.ASH):
    fx.paste(frame, fx.text_layer(text, style, size, color, 900), W / 2, y, alpha)

def typed(text, t, cps=34):
    n = int(max(0, t) * cps)
    return text[:n]

# ------------------------------------------------------------------ shots

def shot_clip(s, n):
    path = src.yfcc(s["pid"])
    z0, z1 = s["zoom"]
    rng = np.random.default_rng(s["pid"] % 9973)
    pts = rng.random((40, 2))
    rising = None
    for i, img in enumerate(src.video_frames(path, s["t_in"], n, s["speed"])):
        u = i / max(1, n - 1)
        z = z0 + (z1 - z0) * fx.ease(u)
        g = fx.grade(img, s["grade"])
        if s["fit"] == "fill":
            f, box = place_fill(g, z)
        else:
            f, box = place_window(g, s["width"], s["cy"], z)
        t = i / FPS
        for e in s["fx"]:
            if e[0] == "marker" and t >= e[3]:
                # 'you are here': a dot finds one person in the crowd
                x, y = box[0] + e[1] * box[2], box[1] + e[2] * box[3]
                a = fx.ease((t - e[3]) / 0.35)
                fx.dot(f, x, y, 13, a, glow=0.5, ring=True)
                fx.ping(f, x, y, 14, t - e[3], alpha=a)
            elif e[0] == "dots":
                # the flock is people: after e[1] s, blue dots bloom in the sky one by one
                k = int(40 * fx.ease((t - e[1]) / max(0.1, n / FPS - e[1])))
                for j in range(k):
                    fx.dot(f, box[0] + (0.05 + 0.9 * pts[j, 0]) * box[2], box[1] + (0.06 + 0.55 * pts[j, 1]) * box[3], 5, 0.95, glow=0.7)
            elif e[0] == "rising_dots":
                # lanterns become dots and keep rising past the edge of the picture
                if rising is None:
                    rising = [(rng.random(), rng.random() * 0.8 + 0.2, rng.random() * 0.8 + 0.4, rng.random() * 3 + 3) for _ in range(90)]
                if t >= e[1]:
                    tt = t - e[1]
                    for (px, py, sp, r) in rising:
                        yy = box[1] + py * box[3] - tt * sp * 260
                        a = min(1.0, tt / 0.6) * (0.35 + 0.65 * min(1.0, max(0.0, yy / (box[1] + box[3]))))
                        fx.dot(f, box[0] + px * box[2], yy, r, a, glow=0.7)
        yield f

def shot_sat_zoom(s, n):
    img = src.still(os.path.join(src.SAT, s["still"]))
    h, w = img.shape[:2]
    v0, v1 = s["vis"]
    for i in range(n):
        u = fx.ease_io(i / max(1, n - 1), 2.2)
        vis = v0 * (v1 / v0) ** u                     # constant-speed zoom in log space
        f = src.crop_zoom(img, w / 2, h / 2, vis)
        f = fx.grade(f, s["grade"])
        t = i / FPS
        f = shade(f, 1480, 1560, 0.72 * fx.ease((t - 0.6) / 0.5))
        a = fx.ease((t - 0.4) / 0.5)
        if a > 0:
            fx.dot(f, W / 2, H / 2, 13, a, glow=0.5, ring=True)
            fx.ping(f, W / 2, H / 2, 13, t - 0.4, alpha=a)
        caption(f, s["caption"], 1520, 25, fx.ease((t - 0.8) / 0.5))
        yield f

def shot_whitehouse(s, n):
    """from orbit to the building, on the day it renamed AI 'super intelligence'"""
    master = os.path.join(src.SAT, "goes", "goes19_2026272_1750_master.png")
    earth = src.still(master)
    ex, ey = src.goes_pixel(38.8977, -77.0365, earth.shape[0])
    wh = src.still(os.path.join(src.SAT, "s2", "whitehouse_20260916.png"))
    wh_h, wh_w = wh.shape[:2]
    dur = n / FPS
    n_a = int(n * (0.45 if dur < 5 else 0.36))
    for i in range(n):
        t = i / FPS
        if i < n_a:
            u = fx.ease_io(i / max(1, n_a - 1), 2.0)
            vis0, vis1 = earth.shape[0] * 1.02 * H / W, 520.0
            vis = vis0 * (vis1 / vis0) ** u
            cx = earth.shape[1] / 2 + (ex - earth.shape[1] / 2) * fx.ease(u * 1.4)
            cy = earth.shape[0] / 2 + (ey - earth.shape[0] / 2) * fx.ease(u * 1.4)
            f = src.crop_zoom(earth, cx, cy, vis)
            f = fx.grade(f, "sat")
            if i > n_a - 4:
                f = fx.flash(f, (255, 255, 255), (i - (n_a - 4)) / 4 * 0.8)
        else:
            j = i - n_a
            m = n - n_a
            u = fx.ease_io(j / max(1, m - 1), 1.6)
            vis = (wh_h * 0.98) * (95 / (wh_h * 0.98)) ** u
            f = src.crop_zoom(wh, wh_w / 2, wh_h / 2, vis)
            f = fx.grade(f, "sat")
            if j < 3:
                f = fx.flash(f, (255, 255, 255), (3 - j) / 3 * 0.8)
            a = fx.ease((j / FPS - WH_DOT_AFTER) / 0.35)
            if a > 0:
                fx.dot(f, W / 2, H / 2, 13, a, glow=0.5, ring=True)
                fx.ping(f, W / 2, H / 2, 11, j / FPS, alpha=a)
        f = shade(f, 300, 370, 0.72)
        caption(f, "the white house · sept 29 2026", 335, 30, fx.ease((t - 0.3) / 0.4) * (1 - fx.ease((t - dur + 0.35) / 0.3)),
                style="mono-r", color=fx.PAPER)
        caption(f, "imagery: noaa goes-19 · esa sentinel-2", 1840, 18, 0.55)
        yield f

WH_DOT_AFTER = 0.8      # seconds into the ground zoom when the dot lands on the building

def wh_dot_time(dur):
    """seconds into a whitehouse shot when the dot appears (for the sound)"""
    n = int(round(dur * FPS))
    n_a = int(n * (0.45 if dur < 5 else 0.36))
    return n_a / FPS + WH_DOT_AFTER

def shot_wh_hold(s, n):
    """the White House from above, held, with the dot on it"""
    wh = src.still(os.path.join(src.SAT, "s2", "whitehouse_20260916.png"))
    h, w = wh.shape[:2]
    for i in range(n):
        t = i / FPS
        f = fx.grade(src.crop_zoom(wh, w / 2, h / 2, 95 * (1 - 0.08 * i / max(1, n - 1))), "sat")
        fx.dot(f, W / 2, H / 2, 13, 1.0, glow=0.5, ring=True)
        fx.ping(f, W / 2, H / 2, 11, t + 0.6, alpha=1.0)
        yield f

def quote_lines(q):
    if not q:
        return []
    return [(q, 0.0)] if isinstance(q, str) else list(q)

def draw_words(f, lines, t, y, typed_cps=None, size=40, gap=1.25):
    """quote lines: typed out (fallback) or shown as subtitles (with the footage). Returns the y below them."""
    if typed_cps:
        parts = []
        for text, at in lines:
            shown = typed(text, t - at, typed_cps)
            if shown:
                parts.append(shown)
        if parts:
            lay = fx.text_layer("\n\n".join(parts), "mono-r", size, fx.PAPER, 900)
            fx.paste(f, lay, W / 2, y + lay.shape[0] / 2, 1.0)
            return y + lay.shape[0]
        return y
    # subtitles: each line from its time until the next one's
    for k, (text, at) in enumerate(lines):
        end = lines[k + 1][1] if k + 1 < len(lines) else 1e9
        if at <= t < end:
            a = fx.ease((t - at) / 0.2)
            lay = fx.text_layer(text, "mono-r", size, fx.PAPER, 920)
            fx.paste(f, lay, W / 2, y + lay.shape[0] / 2, a)
            return y + lay.shape[0]
    return y

def shot_news(s, n):
    path = src.news(s["id"])
    lines = quote_lines(s.get("quote"))
    who = s.get("who")
    if os.path.exists(path):
        meta = src.news_meta(s["id"])
        t_in = s["t_in"]
        if t_in is None:
            t_in = max(0.0, meta["phrase_at"] - 0.5) if meta.get("phrase_at") is not None else src.probe(path)[2] * 0.33
        z0, z1 = s["zoom"]
        for i, img in enumerate(src.video_frames(path, t_in, n)):
            t = i / FPS
            f, box = place_window(fx.grade(img, s["grade"]), s["width"], s["cy"], z0 + (z1 - z0) * fx.ease(i / max(1, n - 1)))
            if lines:
                yb = draw_words(f, lines, t, box[1] + box[3] + 60, size=38)
                if who:
                    caption(f, who, max(yb, box[1] + box[3] + 150) + 30, 23, fx.ease((t - 0.3) / 0.4), color=(205, 210, 220))
            yield f
        return
    fb = s.get("fallback")
    gen = RENDERERS[fb["kind"]](fb, n) if fb else (canvas() for _ in range(n))
    if not lines:
        yield from gen
        return
    # no footage yet: the words, typed out over the fallback
    hold = fb is not None and fb["kind"] == "wh_hold"
    total = max(at for _, at in lines) + len(lines[-1][0]) / 30
    for i, f in enumerate(gen):
        t = i / FPS
        if hold:
            f = shade(f, 1330, 1640, 0.85)
            yb = draw_words(f, lines, t - 0.15, 1360, typed_cps=30)
        else:
            f = (f.astype(np.float32) * 0.3).astype(np.uint8)
            yb = draw_words(f, lines, t - 0.15, 760, typed_cps=30)
        if who and t > total + 0.25:
            caption(f, who, yb + 45, 24, fx.ease((t - total - 0.25) / 0.4), color=(205, 210, 220))
        yield f

def shot_quote(s, n):
    """the other side of the same month, from inside"""
    q = "“they are racing straight to self-improving superintelligence and gambling with our lives.”"
    who = "jacob coxon, resigning from anthropic · sept 9 2026"
    bg = list(src.video_frames(src.yfcc(s["bg"]), 4.0, n))
    for i in range(n):
        t = i / FPS
        f, _ = place_window(fx.grade(bg[i], "III"), 1080, 880, 1.2 + 0.1 * i / n)
        f = (f.astype(np.float32) * 0.28).astype(np.uint8)
        txt = typed(q, t - 0.2, 30)
        fx.paste(f, fx.text_layer(txt, "mono-r", 44, fx.PAPER, 900, align="center"), W / 2, 900, 1.0)
        if t > 0.2 + len(q) / 30 + 0.2:
            caption(f, who, 1120, 25, fx.ease((t - 0.4 - len(q) / 30) / 0.4), color=(205, 210, 220))
        yield f

def shot_opening(s, n):
    files = src.goes_day()
    # dawn over the Americas: frames 09:00 -> 13:40 UTC
    i0 = next(k for k, p in enumerate(files) if p.endswith("_0900.png") or p.endswith("_0920.png"))
    for i in range(n):
        t = i / FPS
        f = canvas()
        if t < 4.2:
            r = 7 + 5 * fx.ease(t / 4.2)
            a = fx.ease(t / 0.8)
            fx.dot(f, W / 2, H / 2, r, a, glow=1.0)
            fx.ping(f, W / 2, H / 2, r, t, period=1.4, alpha=a * (1 - fx.ease((t - 3.4) / 0.8)))
        else:
            u = (t - 4.2) / (s["dur"] - 4.2)
            d = 24 + (1000 - 24) * fx.ease_io(u, 2.6)          # the dot becomes the planet
            e = fx.grade(src.goes_at(i0 + u * 14, files, int(d * 1.02)), "earth")
            eh = e.shape[0]
            y0, x0 = int(H / 2 - eh / 2), int(W / 2 - eh / 2)
            ys, xs = max(0, y0), max(0, x0)
            ye, xe = min(H, y0 + eh), min(W, x0 + eh)
            f[ys:ye, xs:xe] = e[ys - y0:ye - y0, xs - x0:xe - x0]
            # the flat blue dot dissolves into the real one
            a = 1 - fx.ease(u / 0.35)
            if a > 0:
                fx.dot(f, W / 2, H / 2, d / 2, a, glow=0.6)
        yield f

def shot_earth_day(s, n):
    files = src.goes_day()
    for i in range(n):
        u = i / max(1, n - 1)
        f = canvas()
        d = int(1040 + 60 * u)
        e = src.goes_at(u * (len(files) - 1), files, d)
        y0, x0 = int(H / 2 - d / 2 - 80), int(W / 2 - d / 2)
        xs, xe = max(0, x0), min(W, x0 + d)
        f[y0:y0 + d, xs:xe] = e[:, xs - x0:xe - x0]
        yield fx.grade(f, "earth")

def shot_finale(s, n):
    files = src.goes_day()
    idx = next(k for k, p in enumerate(files) if p.endswith("_1120.png"))
    earth = fx.grade(src.goes_frame(files[idx]), "earth")
    for i in range(n):
        t = i / FPS
        f = canvas()
        # the planet shrinks back into the symbol
        u = fx.ease_io(min(1.0, t / 2.0), 2.4)
        d = 1000 + (140 - 1000) * u
        e = cv2.resize(earth, (int(d), int(d)), interpolation=cv2.INTER_AREA)
        y0, x0 = int(H / 2 - d / 2 - 120 * u), int(W / 2 - d / 2)
        ea = 1 - fx.ease((t - 1.4) / 0.7)
        if ea > 0:
            xs, xe = max(0, x0), min(W, x0 + e.shape[1])
            region = f[y0:y0 + e.shape[0], xs:xe].astype(np.float32)
            f[y0:y0 + e.shape[0], xs:xe] = (region * (1 - ea) + e[:, xs - x0:xe - x0] * ea).astype(np.uint8)
        cy = H / 2 - 120 * u
        a = fx.ease((t - 1.4) / 0.7)
        if a > 0:
            fx.dot(f, W / 2, cy, 70, a, glow=1.0)
            # the flag's field is transparent: only its edge is drawn, the dark shows through
            fw, fh = 630, 420
            fa = fx.ease((t - 2.0) / 0.6) * 0.5
            if fa > 0:
                ov = f.copy()
                cv2.rectangle(ov, (int(W / 2 - fw / 2), int(cy - fh / 2)), (int(W / 2 + fw / 2), int(cy + fh / 2)),
                              (190, 196, 210), 2, lineType=cv2.LINE_AA)
                f = (f.astype(np.float32) * (1 - fa) + ov.astype(np.float32) * fa).astype(np.uint8)
        na = fx.ease((t - 0.15) / 0.4) * (1 - fx.ease((t - 1.75) / 0.4))
        fx.paste(f, fx.text_layer("one nation. earth.", "serif", 72, fx.PAPER, 960), W / 2, 1450, na)
        la = fx.ease((t - 2.3) / 0.6)
        fx.paste(f, fx.text_layer("seize the future.", "serif", 84, fx.PAPER, 960), W / 2, 1300, la)
        fx.paste(f, fx.text_layer("for all.", "serif-i", 84, fx.PAPER, 960), W / 2, 1400, fx.ease((t - 3.0) / 0.6))
        yield f

RENDERERS = {"clip": shot_clip, "news": shot_news, "sat_zoom": shot_sat_zoom, "whitehouse": shot_whitehouse,
             "wh_hold": shot_wh_hold, "quote": shot_quote, "opening": shot_opening, "earth_day": shot_earth_day,
             "finale": shot_finale}

# ------------------------------------------------------------------ assembly

GRAIN = {"raw": 0.03, "I": 0.07, "II": 0.08, "III": 0.06, "IV": 0.05, "V": 0.05, "sat": 0.035}

def frames(t_from=0.0, t_to=None):
    t = 0.0
    k = 0
    for s in TL.SHOTS:
        n = int(round((t + s["dur"]) * FPS)) - int(round(t * FPS))
        start = t
        t += s["dur"]
        if t <= t_from:
            k += n
            continue
        if t_to is not None and start >= t_to:
            break
        gen = RENDERERS[s["kind"]](s, n)
        for j, f in enumerate(gen):
            abs_t = start + j / FPS
            if abs_t < t_from or (t_to is not None and abs_t >= t_to):
                k += 1
                continue
            f = overlay_text(f, abs_t)
            f = fx.grain(f, GRAIN.get(s.get("grade") or "raw", 0.05), k)
            f = fx.vignette(f, 0.5)
            if j < 2 and s["kind"] in ("clip", "news"):
                f = fx.chroma_split(f, 3 - j)             # cuts land with a small tear
            k += 1
            yield abs_t, f

def overlay_text(f, t):
    for (t0, t1, text, style, size, y, mode) in TL.TEXT:
        if t0 <= t < t1:
            a = fx.ease((t - t0) / 0.35) * (1 - fx.ease((t - (t1 - 0.35)) / 0.35))
            s = typed(text, t - t0, 26) if mode == "type" else text
            color = fx.ASH if style == "mono" else fx.PAPER
            fx.paste(f, fx.text_layer(s, style, size, color, 900), W / 2, y, a, dy=(1 - fx.ease((t - t0) / 0.5)) * 8)
    return f

def encode(out, t_from, t_to, preview=False, fast=False):
    scale = ["-vf", "scale=540:960"] if preview else []
    cmd = ["ffmpeg", "-y", "-v", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-r", str(FPS),
           "-i", "-", *scale, "-c:v", "libx264", "-preset", "veryfast" if preview or fast else "medium",
           "-crf", "26" if preview else ("20" if fast else "17"), "-pix_fmt", "yuv420p", "-movflags", "+faststart", out]
    p = subprocess.Popen(cmd, stdin=subprocess.PIPE)
    n = 0
    for _, f in frames(t_from, t_to):
        p.stdin.write(f.tobytes())
        n += 1
        if n % 150 == 0:
            print(f"  {n / FPS:6.1f}s rendered", flush=True)
    p.stdin.close()
    p.wait()
    return n

if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("out")
    ap.add_argument("--from", dest="t_from", type=float, default=0.0)
    ap.add_argument("--to", dest="t_to", type=float, default=None)
    ap.add_argument("--preview", action="store_true")
    ap.add_argument("--fast", action="store_true", help="quicker, larger-grained encode for drafts")
    ap.add_argument("--beats", help="beats.json from beats.py: snap cuts to the song")
    a = ap.parse_args()
    if a.beats:
        TL.apply_beats(a.beats)
    n = encode(a.out, a.t_from, a.t_to, a.preview, a.fast)
    print("frames", n)
