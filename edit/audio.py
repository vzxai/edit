"""Soundtrack for the edit.

With --song: the song carries everything; the footage's own sound (chants, the launch, the ice)
comes through underneath at a lower level.
Without it: a temporary score (drone + the footage's own sound + pings when the dot appears),
so the picture can be watched and judged before the song is in.

usage: python3 edit/audio.py OUT.wav [--song SONG.mp3] [--song-start SEC]
"""
import argparse
import os
import subprocess
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import sources as src
import timeline as TL

SR = 48000

def load(path, t_in=0.0, dur=None):
    cmd = ["ffmpeg", "-v", "error", "-ss", f"{t_in:.3f}", "-i", path]
    if dur:
        cmd += ["-t", f"{dur:.3f}"]
    cmd += ["-ac", "2", "-ar", str(SR), "-f", "f32le", "-"]
    raw = subprocess.run(cmd, capture_output=True).stdout
    return np.frombuffer(raw, np.float32).reshape(-1, 2).copy()

def fade(x, a=0.03, b=0.08):
    n = len(x)
    na, nb = min(n, int(a * SR)), min(n, int(b * SR))
    if na: x[:na] *= np.linspace(0, 1, na)[:, None]
    if nb: x[-nb:] *= np.linspace(1, 0, nb)[:, None]
    return x

def place(mix, x, t, gain=1.0):
    i = int(t * SR)
    j = min(len(mix), i + len(x))
    if j > i:
        mix[i:j] += x[:j - i] * gain

def shot_times():
    t, out = 0.0, []
    for s in TL.SHOTS:
        out.append((t, s))
        t += s["dur"]
    return out

def envelope(n, pts):
    """piecewise-linear envelope from (time, value) points"""
    tt = np.arange(n) / SR
    return np.interp(tt, [p[0] for p in pts], [p[1] for p in pts]).astype(np.float32)

def lowpass(x, cutoff):
    a = np.exp(-2 * np.pi * cutoff / SR)
    y = np.empty_like(x)
    acc = np.zeros(x.shape[1], np.float32)
    for i in range(0, len(x), 4096):          # vectorised in blocks via scipy if present
        blk = x[i:i + 4096]
        try:
            from scipy.signal import lfilter
            yb, zf = lfilter([1 - a], [1, -a], blk, axis=0, zi=acc[None, :] * a)
            acc = yb[-1]
            y[i:i + 4096] = yb
        except Exception:
            for k in range(len(blk)):
                acc = (1 - a) * blk[k] + a * acc
                y[i + k] = acc
    return y

def ping(dur=2.4, f=1318.5):
    t = np.arange(int(dur * SR)) / SR
    tone = np.sin(2 * np.pi * f * t) * 0.6 + np.sin(2 * np.pi * f * 2.01 * t) * 0.15
    env = np.exp(-t * 3.2) * (1 - np.exp(-t * 400))
    x = (tone * env).astype(np.float32)
    # a little space
    out = np.zeros(len(x) + int(0.6 * SR), np.float32)
    for d, g in [(0, 1.0), (0.113, 0.35), (0.241, 0.22), (0.389, 0.12)]:
        k = int(d * SR); out[k:k + len(x)] += x * g
    return np.stack([out, np.roll(out, 240)], 1)

def score(total):
    """the temporary score: a low drone that shifts by movement"""
    n = int(total * SR)
    t = np.arange(n, dtype=np.float32) / SR
    rng = np.random.default_rng(3)
    L = np.zeros(n, np.float32); R = np.zeros(n, np.float32)
    def voice(freq, amp_env, det=0.15, pan=0.0):
        a = np.sin(2 * np.pi * freq * t + 0.3 * np.sin(2 * np.pi * 0.07 * t))
        b = np.sin(2 * np.pi * (freq + det) * t)
        v = (a + b) * 0.5 * amp_env
        L[:] += v * (1 - pan) ; R[:] += v * (1 + pan)
    # shot boundaries of the movements (seconds)
    I, II, III, IV, V = 9.0, 40.0, 71.5, 99.5, 111.5
    base = envelope(n, [(0, 0), (3, 0.10), (I, 0.16), (II, 0.20), (III, 0.18), (IV, 0.08), (V, 0.14), (total - 5, 0.18), (total, 0)])
    voice(55.0, base, 0.11, -0.1)
    voice(82.41, base * 0.6, 0.13, 0.1)
    voice(110.0, envelope(n, [(0, 0), (I, 0.05), (II, 0.08), (IV, 0.03), (V, 0.10), (total, 0)]), 0.2, 0.2)
    # II: a heartbeat under the fire
    hb = np.zeros(n, np.float32)
    for bt in np.arange(II, III, 60 / 58):
        for off, g in [(0, 1.0), (0.24, 0.6)]:
            k = int((bt + off) * SR); m = int(0.25 * SR)
            if k + m < n:
                tt = np.arange(m) / SR
                hb[k:k + m] += (np.sin(2 * np.pi * 48 * tt) * np.exp(-tt * 16) * g).astype(np.float32)
    L += hb * 0.35; R += hb * 0.35
    # III: machine tones
    mt = envelope(n, [(III - 1, 0), (III, 0.035), (IV - 0.5, 0.045), (IV, 0)])
    voice(880.0, mt * (0.5 + 0.5 * np.sign(np.sin(2 * np.pi * 7.5 * t))), 0.0, -0.4)
    voice(1318.5, mt * 0.6, 0.0, 0.4)
    # IV -> V: an A major chord opens up
    ch = envelope(n, [(IV, 0), (IV + 3, 0.05), (V, 0.07), (total - 7, 0.12), (total - 1, 0.10), (total, 0)])
    for f_, p_ in [(220.0, -0.3), (277.18, 0.3), (329.63, -0.1), (440.0, 0.1), (554.37, 0.35)]:
        voice(f_, ch, 0.25, p_)
    # air
    noise = rng.normal(0, 1, (n, 2)).astype(np.float32)
    air = lowpass(noise, 900.0) * envelope(n, [(0, 0), (I, 0.05), (II, 0.08), (III, 0.04), (IV, 0.07), (total, 0.03)])[:, None]
    mix = np.stack([L, R], 1) + air
    return mix

def dot_times():
    """when the blue dot arrives on screen (each gets a soft ping)"""
    from render import wh_dot_time
    out = []
    for t, s in shot_times():
        k = s["kind"]
        if k == "opening":
            out.append(t + 0.25)
        elif k == "clip":
            out += [t + e[3] + 0.05 for e in s["fx"] if e[0] == "marker"]
        elif k == "sat_zoom":
            out.append(t + 0.45)
        elif k == "whitehouse":
            out.append(t + wh_dot_time(s["dur"]) + 0.05)
        elif k == "finale":
            out.append(t + 1.4)
    return out

def native(s):
    """the sound a shot brings with it: (path, t_in, gain, is_speech) or None"""
    if s["kind"] == "news":
        path = src.news(s["id"])
        if os.path.exists(path):
            meta = src.news_meta(s["id"])
            t_in = s["t_in"]
            if t_in is None:
                t_in = max(0.0, meta["phrase_at"] - 0.5) if meta.get("phrase_at") is not None else 0.0
            return path, t_in, s["audio"], bool(s.get("quote"))
        s = s.get("fallback") or {}
    if s.get("kind") == "clip" and s.get("audio", 0) > 0:
        return src.yfcc(s["pid"]), s["t_in"], s["audio"], False
    return None

def build(out, song=None, song_start=0.0):
    total = TL.total()
    n = int(total * SR)
    bed = np.zeros((n, 2), np.float32)
    if song:
        s = load(song, song_start, total)
        place(bed, fade(s, 0.01, 1.5), 0.0, 1.0)
        native_gain = 0.35
    else:
        bed += score(total)
        native_gain = 1.0
    mix = np.zeros((n, 2), np.float32)
    duck = [(0.0, 1.0)]
    for t, s in shot_times():
        src_ = native(s)
        if not src_:
            continue
        path, t_in, gain, speech = src_
        x = load(path, t_in, s["dur"] + 0.25)
        if not len(x):
            continue
        pk = np.max(np.abs(x)) + 1e-6
        if speech:
            # someone speaks: their voice leads, the music steps back
            place(mix, fade(x / pk * 0.8, 0.02, 0.2), t, gain)
            duck += [(t - 0.15, 1.0), (t + 0.1, 0.32), (t + s["dur"] - 0.1, 0.32), (t + s["dur"] + 0.25, 1.0)]
        else:
            place(mix, fade(x / pk * 0.5, 0.04, 0.25), t, gain * native_gain)
    duck.append((total, 1.0))
    duck.sort()
    mix += bed * envelope(n, duck)[:, None]
    for tp in dot_times():
        place(mix, ping(), tp, 0.22 if song else 0.35)
    mix = np.tanh(mix * 1.1) * 0.9
    tmp = out + ".raw.f32"
    mix.astype(np.float32).tofile(tmp)
    subprocess.run(["ffmpeg", "-y", "-v", "error", "-f", "f32le", "-ar", str(SR), "-ac", "2", "-i", tmp,
                    "-af", "loudnorm=I=-14:TP=-1.5:LRA=11", "-ar", str(SR), out], check=True)
    os.remove(tmp)
    print("wrote", out, f"{total:.1f}s")

if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("out")
    ap.add_argument("--song")
    ap.add_argument("--song-start", type=float, default=0.0)
    ap.add_argument("--beats", help="beats.json from beats.py: snap cuts to the song")
    a = ap.parse_args()
    if a.beats:
        TL.apply_beats(a.beats)
    build(a.out, a.song, a.song_start)
