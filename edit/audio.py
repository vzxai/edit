"""Soundtrack for the edit.

With --song: the song carries everything. When someone speaks the music steps back; the footage's own
sound (chants, the launch, the ice) comes through underneath. The only sound of ours is one signal from
the dot, in the silence at the end.
Without it: a temporary score (drone + the footage's own sound + pings when the dot appears).

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

def load(path, t_in=0.0, dur=None, af=None):
    cmd = ["ffmpeg", "-v", "error", "-ss", f"{t_in:.3f}", "-i", path]
    if dur:
        cmd += ["-t", f"{dur:.3f}"]
    if af:
        cmd += ["-af", af]
    cmd += ["-ac", "2", "-ar", str(SR), "-f", "f32le", "-"]
    raw = subprocess.run(cmd, capture_output=True).stdout
    return np.frombuffer(raw, np.float32).reshape(-1, 2).copy()

# a voice from the news: cleaned up and evened out, so every speaker sits at the same level over the music
VOICE_AF = "highpass=f=90,lowpass=f=9500,acompressor=threshold=0.06:ratio=4:attack=5:release=120:makeup=2"
VOICE_RMS = -18.0          # dBFS, averaged over the parts where someone is talking

def voice_level(x):
    """scale speech so its active RMS is VOICE_RMS, then round off the peaks"""
    fr = int(0.05 * SR)
    k = len(x) // fr
    if k == 0:
        return x
    e = np.sqrt((x[:k * fr] ** 2).reshape(k, fr, -1).mean(axis=(1, 2)) + 1e-12)
    act = e > e.max() * 10 ** (-25 / 20)
    rms = np.sqrt(np.mean(e[act] ** 2))
    y = x * (10 ** (VOICE_RMS / 20) / rms)
    return (np.tanh(y / 0.89) * 0.89).astype(np.float32)

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

def b_(n):
    return TL.b(n)

def score(total):
    """the temporary score: a low drone that shifts by section"""
    n = int(total * SR)
    t = np.arange(n, dtype=np.float32) / SR
    rng = np.random.default_rng(3)
    L = np.zeros(n, np.float32); R = np.zeros(n, np.float32)
    def voice(freq, amp_env, det=0.15, pan=0.0):
        a = np.sin(2 * np.pi * freq * t + 0.3 * np.sin(2 * np.pi * 0.07 * t))
        b = np.sin(2 * np.pi * (freq + det) * t)
        v = (a + b) * 0.5 * amp_env
        L[:] += v * (1 - pan) ; R[:] += v * (1 + pan)
    # where the edit's sections start (seconds)
    I, II, III, IV, V = TL.VERSE, TL.DROP, TL.BREAK, TL.BUILD + b_(29), TL.FINAL
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

def dot_times(song=False):
    """when the blue dot arrives on screen (each gets a soft ping). With the song, only the last one:
    the signal that goes out in the silence after the music stops."""
    from render import wh_dot_time
    out = []
    for t, s in shot_times():
        k = s["kind"]
        if k == "finale":
            out.append(t + s.get("land", 2.3))
        elif song:
            continue
        elif k == "opening":
            out += [t + p + 0.02 for p in s["pulses"]]
        elif k == "clip":
            out += [t + e[3] + 0.05 for e in s["fx"] if e[0] == "marker"]
        elif k == "sat_zoom":
            out.append(t + 0.45)
        elif k == "whitehouse":
            out.append(t + wh_dot_time(s["dur"]) + 0.05)
    return out

def native(s):
    """the sound a shot brings with it: dict(path, t_in, gain, speech, duck, a_out) or None"""
    if s["kind"] == "news":
        path = src.news(s["id"])
        if os.path.exists(path):
            meta = src.news_meta(s["id"])
            t_in = s["t_in"]
            if t_in is None:
                t_in = max(0.0, meta["phrase_at"] - 0.5) if meta.get("phrase_at") is not None else 0.0
            return dict(path=path, t_in=t_in, gain=s["audio"], speech=s.get("speech", bool(s.get("quote"))),
                        duck=s.get("duck", 0.18), a_out=s.get("a_out"))
        s = s.get("fallback") or {}
    if s.get("kind") == "clip" and s.get("audio", 0) > 0:
        return dict(path=src.yfcc(s["pid"]), t_in=s["t_in"], gain=s["audio"], speech=False, duck=1.0, a_out=None)
    return None

def build(out, song=None, song_start=0.0):
    total = TL.total()
    n = int(total * SR)
    bed = np.zeros((n, 2), np.float32)
    if song:
        s = load(song, song_start, total)
        place(bed, fade(s, 0.01, 0.3), 0.0, 1.0)
        native_gain = 0.35
    else:
        bed += score(total)
        native_gain = 1.0
    mix = np.zeros((n, 2), np.float32)
    duck = np.ones(n, np.float32)
    for t, s in shot_times():
        a = native(s)
        if not a:
            continue
        length = s["dur"] + 0.25
        if a["a_out"] is not None:
            length = min(length, a["a_out"] - a["t_in"])
        x = load(a["path"], a["t_in"], length, af=VOICE_AF if a["speech"] else None)
        if not len(x):
            continue
        pk = np.max(np.abs(x)) + 1e-6
        if a["speech"]:
            # someone speaks: their voice leads, the music steps back (and comes back after)
            place(mix, fade(voice_level(x), 0.02, 0.08 if a["a_out"] else 0.2), t, a["gain"])
            end = t + len(x) / SR
            env = envelope(n, [(0, 1.0), (t - 0.15, 1.0), (t + 0.1, a["duck"]), (end - 0.05, a["duck"]),
                               (end + 0.3, 1.0), (total + 1, 1.0)])
            duck = np.minimum(duck, env)
        else:
            place(mix, fade(x / pk * 0.5, 0.04, 0.25), t, a["gain"] * native_gain)
    mix += bed * duck[:, None]
    for tp in dot_times(song=bool(song)):
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
    a = ap.parse_args()
    build(a.out, a.song, a.song_start)
