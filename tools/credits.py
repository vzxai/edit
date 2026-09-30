"""Write CREDITS.md for what is actually in the cut: CC footage (with fallbacks where news clips are
still missing), fetched news clips, imagery, symbol and music.  usage: python3 tools/credits.py"""
import csv
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "edit"))
import timeline as TL  # noqa: E402

def main():
    yfcc = {int(r["photoid"]): r for r in csv.DictReader(open(os.path.join(ROOT, "edit", "credits_yfcc.tsv")), delimiter="\t")}
    news_dir = os.path.join(ROOT, "footage", "news")
    used, news = [], []
    for s in TL.SHOTS:
        if s["kind"] == "news":
            meta = os.path.join(news_dir, f"{s['id']}.json")
            if os.path.exists(os.path.join(news_dir, f"{s['id']}.mp4")):
                news.append(json.load(open(meta)) if os.path.exists(meta) else {"id": s["id"]})
                continue
            s = s.get("fallback") or {}
        if s.get("kind") == "clip":
            used.append(s["pid"])
        elif s.get("kind") == "quote":
            used.append(s["bg"])
    lines = ["# credits", ""]
    if news:
        lines += ["News and public footage, used for commentary, in order of appearance:", ""]
        for m in news:
            lines.append(f"- {m.get('credit') or m['id']}: \"{m.get('title', '')}\" ({m.get('channel', '')}), {m.get('source', '')}")
        lines.append("")
    lines += ["Footage: YFCC100M / Multimedia Commons, Flickr videos shared under Creative Commons, in order of appearance.", ""]
    seen = set()
    for pid in used:
        if pid in seen or pid not in yfcc:
            continue
        seen.add(pid)
        r = yfcc[pid]
        lines.append(f"- \"{r['title'] or '(untitled)'}\" by {r['author']} ({r['taken'][:4]}), "
                     f"{r['license'].replace(' License', '')}, {r['source']}")
    lines += ["", "Earth: NOAA GOES-19 ABI full disk, 2026-09-29 (public domain).",
              "Ground: contains modified Copernicus Sentinel data 2026 (Washington DC 2026-09-16; Abilene TX 2026-09-15).",
              "Symbol: the One World Flag by Thomas Mandl (2016), public domain.",
              "Music: \"i feel weird\" by meat computer (2026).",
              "", "The news footage belongs to its owners and is quoted here for commentary and criticism.",
              "Everything else of ours (the words, the dot, the design) is CC BY-NC-SA 4.0: some of the Creative Commons "
              "footage is ShareAlike or NonCommercial, so the piece is too."]
    open(os.path.join(ROOT, "CREDITS.md"), "w").write("\n".join(lines) + "\n")
    print(f"{len(seen)} CC clips, {len(news)} news clips credited")

if __name__ == "__main__":
    main()
