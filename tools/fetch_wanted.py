#!/usr/bin/env python3
"""Fetch the song and the news clips listed in edit/wanted.json. Run this on a normal computer
(the cloud sandbox the edit was made in can't reach YouTube or SoundCloud).

  pip install -U yt-dlp          # plus ffmpeg on PATH
  python tools/fetch_wanted.py                 # song + every priority-A clip
  python tools/fetch_wanted.py --all           # A and B
  python tools/fetch_wanted.py --only thiel_endure --url https://youtu.be/... [--start 43:10]

For each clip it finds a video (the listed URLs first, then YouTube searches), reads the video's
English captions to find the clip's `phrase`, and downloads only the seconds around it.
B-roll without a phrase: videos up to 90 seconds are kept whole. For longer ones it saves a small
preview and a contact sheet (a frame every few seconds, labelled) in footage/_proxy/ and asks for
--start: look at the sheet, pick where the moment begins, and run it again with --only/--url/--start.

Writes footage/news/<id>.mp4 (<=720p, original sound), <id>.vtt (captions for that window,
starting at 0) and <id>.json (source, title, channel, date, cut times), plus music/i-feel-weird.mp3.
At the end it prints what it couldn't find, so a person (or agent) can pick those by hand.
"""
import argparse
import json
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

try:
    import yt_dlp
    from yt_dlp.utils import download_range_func
except ImportError:
    sys.exit("yt-dlp is missing: pip install -U yt-dlp")

ROOT = Path(__file__).resolve().parent.parent
WANTED = ROOT / "edit" / "wanted.json"
NEWS = ROOT / "footage" / "news"
FMT = "bv*[height<=720][ext=mp4]+ba[ext=m4a]/bv*[height<=720]+ba/b[height<=720]/b"
MAX_WHOLE = 90           # seconds: b-roll videos up to this long are kept whole
BROLL_LEN = 12           # seconds cut from longer b-roll at --start
PROXY = ROOT / "footage" / "_proxy"


def ts(s):
    """'1:02:03.5' or '63.5' -> seconds"""
    if s is None:
        return None
    parts = [float(p) for p in str(s).split(":")]
    t = 0.0
    for p in parts:
        t = t * 60 + p
    return t


def norm(text):
    return re.findall(r"[a-z0-9']+", text.lower().replace("-", " ").replace("%", " percent"))


def parse_vtt(path):
    """[(seconds, word)] from a caption file. YouTube auto-captions carry word timings
    (word<00:00:01.120><c> next</c>) and repeat the previous line as plain text; only the timed
    lines are read then. Plain captions get their cue's time spread across the words."""
    text = Path(path).read_text(encoding="utf-8", errors="replace")
    timed = "<c>" in text
    cue_re = re.compile(r"(?:(\d+):)?(\d+):(\d+\.\d+) --> (?:(\d+):)?(\d+):(\d+\.\d+)")
    words, last_plain = [], None
    for block in re.split(r"\n\n+", text.replace("\r", "")):
        m = cue_re.search(block)
        if not m:
            continue
        g = m.groups()
        start = int(g[0] or 0) * 3600 + int(g[1]) * 60 + float(g[2])
        end = int(g[3] or 0) * 3600 + int(g[4]) * 60 + float(g[5])
        body = block[m.end():].split("\n")[1:]
        for line in body:
            if timed:
                if "<" not in line:
                    continue
                t = start
                for tok in re.split(r"(<(?:\d+:)?\d+:\d+\.\d+>)", line):
                    mm = re.match(r"<(?:(\d+):)?(\d+):(\d+\.\d+)>", tok)
                    if mm:
                        t = int(mm.group(1) or 0) * 3600 + int(mm.group(2)) * 60 + float(mm.group(3))
                        continue
                    for w in norm(re.sub(r"<[^>]+>", "", tok)):
                        words.append((t, w))
            else:
                ws = norm(re.sub(r"<[^>]+>", "", line))
                if not ws or line.strip() == last_plain:
                    continue
                last_plain = line.strip()
                step = max(0.05, (end - start) / len(ws))
                words += [(start + i * step, w) for i, w in enumerate(ws)]
    words.sort(key=lambda x: x[0])          # stable: same-time words keep their order
    out = []
    for t, w in words:
        if out and out[-1] == (t, w):
            continue
        out.append((t, w))
    return out


def find_phrase(words, phrase):
    """time of the first matched word of the best in-order match of phrase (>=75% of its words;
    each next word may be up to 2 words further on, to survive caption mistakes)"""
    target = norm(phrase)
    best, best_t = 0.0, None
    for i in range(len(words)):
        j, hit, first = i, 0, None
        for w in target:
            k = j
            while k < min(len(words), j + 3) and words[k][1] != w:
                k += 1
            if k < min(len(words), j + 3):
                hit += 1
                first = k if first is None else first
                j = k + 1
        score = hit / len(target)
        if score > best and first is not None:
            best, best_t = score, words[first][0]
        if best == 1.0:
            break
    return (best_t, best) if best >= 0.75 else (None, best)


def info(url_or_search, n=None):
    opts = {"quiet": True, "no_warnings": True, "skip_download": True, "extract_flat": n is not None}
    with yt_dlp.YoutubeDL(opts) as y:
        r = y.extract_info(url_or_search, download=False)
    if n is not None:
        return [e for e in (r.get("entries") or []) if e][:n]
    return r


def captions(url, tmp):
    opts = {"quiet": True, "no_warnings": True, "skip_download": True, "writesubtitles": True,
            "writeautomaticsub": True, "subtitleslangs": ["en", "en-US", "en-orig", "en.*"],
            "subtitlesformat": "vtt", "outtmpl": str(Path(tmp) / "cap.%(ext)s")}
    with yt_dlp.YoutubeDL(opts) as y:
        y.download([url])
    files = sorted(Path(tmp).glob("cap*.vtt"))
    return files[0] if files else None


def download(url, out_mp4, start=None, end=None):
    opts = {"quiet": True, "no_warnings": True, "format": FMT, "merge_output_format": "mp4",
            "outtmpl": str(out_mp4.with_suffix(".%(ext)s")), "overwrites": True}
    if start is not None:
        opts["download_ranges"] = download_range_func(None, [(max(0.0, start), end)])
        opts["force_keyframes_at_cuts"] = True
    with yt_dlp.YoutubeDL(opts) as y:
        y.download([url])
    return out_mp4.exists()


def proxy_sheet(cid, url, dur):
    """small preview + a labelled contact sheet, so a person or an agent can choose --start by eye"""
    PROXY.mkdir(parents=True, exist_ok=True)
    proxy = PROXY / f"{cid}.mp4"
    opts = {"quiet": True, "no_warnings": True, "format": "bv*[height<=360]+ba/b[height<=360]/worst",
            "merge_output_format": "mp4", "outtmpl": str(proxy.with_suffix(".%(ext)s")), "overwrites": True}
    with yt_dlp.YoutubeDL(opts) as y:
        y.download([url])
    step = max(2, int(dur // 60) + 1)                       # at most ~60 frames
    sheet = PROXY / f"{cid}_sheet.jpg"
    vf = (f"fps=1/{step},scale=320:-2,drawtext=text='%{{pts\\:hms}}':x=6:y=6:fontsize=18:"
          f"fontcolor=yellow:box=1:boxcolor=black@0.6,tile=6x10")
    # drawtext's timestamp is in the sampled stream's time; setpts keeps it in source seconds
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", str(proxy), "-vf", vf, "-frames:v", "1", str(sheet)])
    return sheet


def write_window_vtt(words, start, end, path):
    """captions for the downloaded window, re-timed to start at 0 (one word per cue)"""
    lines = ["WEBVTT", ""]
    sel = [(t - start, w) for t, w in words if start <= t < end]
    for i, (t, w) in enumerate(sel):
        t2 = sel[i + 1][0] if i + 1 < len(sel) else t + 0.4
        f = lambda x: f"{int(x // 3600):02d}:{int(x % 3600 // 60):02d}:{x % 60:06.3f}"
        lines += [f"{f(t)} --> {f(max(t2, t + 0.05))}", w, ""]
    Path(path).write_text("\n".join(lines), encoding="utf-8")


def fetch_clip(c, url_override=None, start_override=None):
    out = NEWS / f"{c['id']}.mp4"
    if out.exists() and not url_override:
        return "have"
    candidates = [url_override] if url_override else list(c.get("urls", []))
    if not url_override:
        for q in c.get("searches", []):
            try:
                candidates += [e.get("url") or f"https://www.youtube.com/watch?v={e['id']}" for e in info(q, 8)]
            except Exception as e:
                print(f"  search failed: {q}: {e}")
    tried = set()
    for url in candidates:
        if not url or url in tried:
            continue
        tried.add(url)
        try:
            meta = info(url)
        except Exception as e:
            print(f"  skip {url}: {e}")
            continue
        dur = meta.get("duration") or 0
        start = end = None
        words = []
        if start_override is not None:
            start = ts(start_override)
            end = start + (c.get("pre", 0) + c.get("post", 0) if c.get("phrase") else BROLL_LEN)
        elif c.get("phrase"):
            with tempfile.TemporaryDirectory() as tmp:
                try:
                    vtt = captions(url, tmp)
                except Exception:
                    vtt = None
                if not vtt:
                    print(f"  no captions: {meta.get('title')}")
                    continue
                words = parse_vtt(vtt)
            t, score = find_phrase(words, c["phrase"])
            if t is None:
                print(f"  phrase not found ({score:.0%}): {meta.get('title')}")
                continue
            start, end = t - c.get("pre", 4), t + c.get("post", 4)
        elif dur and dur <= MAX_WHOLE:
            start = end = None                     # keep it whole
        else:
            sheet = proxy_sheet(c["id"], url, dur)
            print(f"  long video ({dur}s): {meta.get('title')}\n  pick the moment on {sheet} then run:\n"
                  f"  python tools/fetch_wanted.py --only {c['id']} --url {url} --start m:ss")
            return "pick"
        print(f"  <- {meta.get('title')} [{meta.get('channel') or meta.get('uploader')}] "
              f"{'' if start is None else f'{start:.1f}-{end:.1f}s'}")
        NEWS.mkdir(parents=True, exist_ok=True)
        if not download(url, out, start, end):
            print("  download failed")
            continue
        if words and start is not None:
            write_window_vtt(words, max(0.0, start), end, out.with_suffix(".vtt"))
        json.dump({"id": c["id"], "source": url, "title": meta.get("title"),
                   "channel": meta.get("channel") or meta.get("uploader"), "upload_date": meta.get("upload_date"),
                   "cut_start": start, "cut_end": end, "phrase": c.get("phrase"),
                   "phrase_at": None if start is None or not c.get("phrase") else c.get("pre", 4),
                   "credit": c.get("credit")}, open(out.with_suffix(".json"), "w"), indent=1)
        return "ok"
    return "missing"


def fetch_song(s, url=None):
    out = ROOT / s["out"]
    if out.exists() and not url:
        return "have"
    out.parent.mkdir(parents=True, exist_ok=True)
    cands = [url] if url else []
    for q in s["searches"]:
        try:
            cands += [e.get("url") or e.get("webpage_url") for e in info(q, 5)]
        except Exception as e:
            print(f"  search failed: {q}: {e}")
    for u in cands:
        if not u:
            continue
        try:
            m = info(u)
        except Exception:
            continue
        title = f"{m.get('title', '')} {m.get('uploader', '')} {m.get('artist', '')}".lower()
        dur = m.get("duration") or 0
        if "weird" not in title or not (120 <= dur <= 155):
            continue
        opts = {"quiet": True, "no_warnings": True, "format": "bestaudio/best",
                "outtmpl": str(out.with_suffix(".%(ext)s")),
                "postprocessors": [{"key": "FFmpegExtractAudio", "preferredcodec": "mp3", "preferredquality": "0"}]}
        with yt_dlp.YoutubeDL(opts) as y:
            y.download([u])
        print(f"  <- {m.get('title')} [{m.get('uploader')}] {dur}s")
        return "ok" if out.exists() else "failed"
    return "missing"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--all", action="store_true", help="also fetch priority B clips")
    ap.add_argument("--only", help="comma-separated clip ids (or 'song')")
    ap.add_argument("--url", help="use this URL for --only (one id)")
    ap.add_argument("--start", help="m:ss where the moment starts, for long b-roll or a manual cut")
    ap.add_argument("--no-song", action="store_true")
    a = ap.parse_args()
    if not shutil.which("ffmpeg"):
        sys.exit("ffmpeg is missing (needed to cut and merge)")
    w = json.load(open(WANTED))
    only = set(a.only.split(",")) if a.only else None
    report = {}
    if not a.no_song and (only is None or "song" in only):
        print("song: i feel weird - meat computer")
        report["song"] = fetch_song(w["song"], a.url if only == {"song"} else None)
    for c in w["clips"]:
        if only is not None and c["id"] not in only:
            continue
        if only is None and c["priority"] != "A" and not a.all:
            continue
        print(f"{c['id']}: {c['what'][:90]}")
        report[c["id"]] = fetch_clip(c, a.url if only and len(only) == 1 else None, a.start)
    print("\n== report")
    for k, v in report.items():
        print(f"  {v:8s} {k}")
    missing = [k for k, v in report.items() if v not in ("ok", "have", "pick")]
    picks = [k for k, v in report.items() if v == "pick"]
    if picks:
        print("\nneeds a start time (see footage/_proxy/<id>_sheet.jpg): " + ", ".join(picks))
    if missing:
        print("\nnot found automatically: " + ", ".join(missing))
        print("find each by hand, then: python tools/fetch_wanted.py --only ID --url URL [--start m:ss]")


if __name__ == "__main__":
    main()
