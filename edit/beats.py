"""Listen to the song so the cuts can land on it.

Finds the beat grid, the strongest onsets and the section boundaries, prints a map of the song
(and saves it as JSON). render.py/audio.py read the JSON to snap every cut to the nearest beat.

usage: python3 edit/beats.py SONG.mp3 OUT.json
"""
import json
import sys

import librosa
import numpy as np

def analyse(path):
    y, sr = librosa.load(path, sr=22050, mono=True)
    dur = len(y) / sr
    tempo, beats = librosa.beat.beat_track(y=y, sr=sr, units="time", trim=False)
    onset_env = librosa.onset.onset_strength(y=y, sr=sr)
    onsets = librosa.onset.onset_detect(onset_envelope=onset_env, sr=sr, units="time", backtrack=True)
    # loudness curve (0.5 s hops) to see where it builds and where it breathes
    rms = librosa.feature.rms(y=y, frame_length=2048, hop_length=11025)[0]
    rms_db = librosa.amplitude_to_db(rms, ref=np.max)
    # sections: agglomerative segmentation on chroma + mfcc
    chroma = librosa.feature.chroma_cqt(y=y, sr=sr)
    mfcc = librosa.feature.mfcc(y=y, sr=sr, n_mfcc=13)
    feats = np.vstack([librosa.util.normalize(chroma, axis=1), librosa.util.normalize(mfcc, axis=1)])
    k = int(np.clip(round(dur / 20), 4, 10))
    bounds = librosa.segment.agglomerative(feats, k)
    bound_t = sorted(set([0.0] + list(librosa.frames_to_time(bounds, sr=sr)) + [dur]))
    # strongest hits (for flashes / hard cuts)
    strength = np.interp(onsets, librosa.times_like(onset_env, sr=sr), onset_env)
    hits = [float(t) for t, s in zip(onsets, strength) if s > np.percentile(strength, 90)]
    return dict(duration=dur, tempo=float(np.atleast_1d(tempo)[0]), beats=[float(b) for b in beats],
                onsets=[float(o) for o in onsets], hits=hits, sections=[float(b) for b in bound_t],
                loudness_db_halfsec=[float(v) for v in rms_db])

def snap(t, grid, tol=0.18):
    """nearest grid time within tol, else t"""
    if not grid:
        return t
    g = np.asarray(grid)
    i = int(np.argmin(np.abs(g - t)))
    return float(g[i]) if abs(g[i] - t) <= tol else t

if __name__ == "__main__":
    info = analyse(sys.argv[1])
    json.dump(info, open(sys.argv[2], "w"), indent=1)
    print(f"duration {info['duration']:.2f}s  tempo {info['tempo']:.1f} bpm  beats {len(info['beats'])}  hits {len(info['hits'])}")
    print("sections:", " | ".join(f"{a:.1f}-{b:.1f}" for a, b in zip(info["sections"][:-1], info["sections"][1:])))
    lo = info["loudness_db_halfsec"]
    bars = "".join(" ▁▂▃▄▅▆▇█"[int(np.clip((v + 40) / 40 * 8, 0, 8))] for v in lo[::2])
    print("energy (1 char/s):", bars)
