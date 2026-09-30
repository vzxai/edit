"""Transmissions: the edit as still images (a carousel), plus printables for the symbol.

usage: python3 brand/posters.py OUTDIR
"""
import os
import sys

import numpy as np
from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "edit"))
import fx
import render as R
import timeline as TL
from fx import H, W

def shot_frame(pred, t_rel):
    """one frame from a shot of the edit (without the edit's own words)"""
    s = next(x for x in TL.SHOTS if pred(x))
    n = int(round(s["dur"] * fx.FPS))
    k = min(n - 1, int(t_rel * fx.FPS))
    for i, f in enumerate(R.RENDERERS[s["kind"]](s, n)):
        if i == k:
            return f
    return f

def words(f, lines):
    for (text, style, size, y, color) in lines:
        fx.paste(f, fx.text_layer(text, style, size, color, 900), W / 2, y, 1.0)
    return f

def finish(f, i):
    return fx.vignette(fx.grain(f, 0.06, i), 0.5)

def card_you_are_here():
    f = R.canvas()
    fx.dot(f, W / 2, H / 2, 16, 1.0, glow=1.0)
    for r, a in [(40, 0.5), (72, 0.25)]:
        fx._blend_ring(f, W / 2, H / 2, r, fx.SIGNAL, a, 2)
    return words(f, [("you are here.", "serif", 70, 1160, fx.PAPER)])

def carousel():
    P, A = fx.PAPER, fx.ASH
    clip = lambda pid: (lambda s: s.get("pid") == pid)
    kind = lambda k: (lambda s: s["kind"] == k)
    nid = lambda i: (lambda s: s.get("id") == i)
    cards = [
        card_you_are_here(),
        words(shot_frame(clip(4405279512), 1.8), [
            ("if you feel weird lately,", "serif", 62, 1400, P),
            ("you're not broken.\nyou're paying attention.", "serif", 62, 1520, P)]),
        words(shot_frame(nid("inauguration_ceos"), 1.2), [
            ("1% of us own 43.8%\nof the world's wealth.", "mono-r", 50, 1420, P),
            ("the poorer half owns 0.52%\noxfam · jan 2026", "mono", 26, 1560, A)]),
        words(shot_frame(clip(4340515506), 2.5), [
            ("their plan for the end of the world\nis to leave.", "serif", 62, 1440, P)]),
        words(shot_frame(clip(3772095704), 1.0), [
            ("85 seconds to midnight.", "mono-r", 50, 1400, P),
            ("doomsday clock · jan 27 2026\nthe closest it has ever been", "mono", 26, 1500, A)]),
        shot_frame(nid("trump_si"), 4.4),
        shot_frame(kind("quote"), 3.9),
        words(shot_frame(kind("earth_day"), 1.5), [
            ("there is no leaving.\nthere is only here,\nand each other.", "serif", 62, 1560, P)]),
        words(shot_frame(nid("bangladesh_aug5"), 0.8), [
            ("they have the money.\nwe have the numbers.", "serif", 64, 1440, P)]),
        words(shot_frame(clip(8669531576), 2.3), [
            ("it has never taken everyone.", "serif", 60, 1420, P),
            ("only enough of us,\ntogether, at once.", "serif", 60, 1540, P)]),
        shot_frame(kind("finale"), 1.0),
        shot_frame(kind("finale"), 6.7),
    ]
    return cards

def printable_flag(path, dpi=300):
    """A4 portrait: the flag (its field is the paper — hold it up and the world shows through)"""
    w, h = int(8.27 * dpi), int(11.69 * dpi)
    im = Image.new("RGB", (w, h), (246, 244, 239))
    f = np.array(im)
    fw, fh = int(w * 0.78), int(w * 0.78 * 2 / 3)
    cy = int(h * 0.40)
    fx.dot(f, w / 2, cy, fh * 0.2, 1.0, glow=0.0)
    out = Image.fromarray(f)
    lay = fx.text_layer("seize the future. for all.", "serif", 120, (20, 24, 40), int(w * 0.8), shadow=False)
    small = fx.text_layer("a blue dot on a transparent field: the one world flag (thomas mandl, 2016, public domain).\n"
                          "cut out the dot. put it on a window, a wall, a sign, a jacket.\nthe background is wherever you are.",
                          "mono", 34, (70, 76, 90), int(w * 0.8), shadow=False)
    arr = np.array(out)
    fx.paste(arr, lay, w / 2, int(h * 0.70))
    fx.paste(arr, small, w / 2, int(h * 0.82))
    Image.fromarray(arr).save(path, dpi=(dpi, dpi))

def printable_stickers(path, dpi=300):
    """US letter: 20 dots to cut out, each 1.5 in, with a thin cutting guide"""
    w, h = int(8.5 * dpi), int(11 * dpi)
    f = np.full((h, w, 3), 255, np.uint8)
    r = int(0.75 * dpi * 0.8)
    for row in range(5):
        for col in range(4):
            cx = int((col + 0.5) * w / 4)
            cy = int((row + 0.5) * h / 5)
            fx._blend_ring(f, cx, cy, int(0.75 * dpi), (0.8, 0.8, 0.8), 1.0, 2)
            fx.dot(f, cx, cy, r, 1.0, glow=0.0)
    Image.fromarray(f).save(path, dpi=(dpi, dpi))

if __name__ == "__main__":
    out = sys.argv[1]
    os.makedirs(out, exist_ok=True)
    for i, f in enumerate(carousel(), 1):
        Image.fromarray(finish(f, i)).save(os.path.join(out, f"transmission_{i:02d}.png"))
        print("card", i)
    printable_flag(os.path.join(out, "print_flag_A4.png"))
    printable_stickers(os.path.join(out, "print_dots_letter.png"))
    print("done")
