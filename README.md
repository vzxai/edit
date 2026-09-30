# seize the future. for all.

A vertical (9:16) found-footage edit for TikTok and Reels, set to **"i feel weird" by meat computer** (2:16, released Sept 2 2026).
It is corecore and political on purpose: against end-times fascism, the race to superintelligence and the concentration of wealth and power in a few hands, and a call for our generation to take the future back. We are nationalists of one nation: the nation of earth.
The symbol is the **One World Flag**, a blue dot on a transparent field.

```
0   you are here            a dot in the dark becomes the planet (GOES-19, Sept 29 2026)
I   i feel weird            screens, crowds, conveyor belts, billionaires in space   "you're not broken. you're paying attention."
                            zuckerberg: "fewer than three friends" · bezos: "you guys paid for all this"
II  their plan is to leave  "1% of us own 43.8% of the world's wealth." · thiel hesitates on whether humanity should endure
                            karp: "scare our enemies and, on occasion, kill them" · masks, fire, ice · "85 seconds to midnight."
                            a night launch: "their plan for the end of the world is to leave."
III super                   stargate from orbit · hinton's warning · orbit -> the White House on Sept 29 2026:
                            "SI instead of AI… super." · "tremendous self-policing" · huang: "zero percent chance"
                            coxon, quitting anthropic: "gambling with our lives."
IV  there is no leaving     one whole day of the Earth in four seconds; children
V   seize the future        nepal, sri lanka, bangladesh, the one piece flag, serbia's silence, oakland's general strike
                            "they have the money. we have the numbers." · lanterns become blue dots
                            "one nation. earth."  "seize the future. for all."
```

## what's here

| path | what |
|---|---|
| `brand/MANIFESTO.md` | the poem, the symbol, the lines |
| `brand/symbol/` | the flag and the dot as SVG and transparent PNG, plus avatars |
| `brand/posters.py` | the edit as a 9-card carousel ("transmissions") plus printables: an A4 dot poster and a sheet of dots to cut out |
| `brand/fonts/` | Instrument Serif (words), IBM Plex Mono (facts), Inter (all OFL-licensed) |
| `edit/timeline.py` | the edit, shot by shot, and every word on screen |
| `edit/render.py` | the renderer (1080x1920, 30 fps) |
| `edit/audio.py` | the soundtrack: the song, or a temporary score until the song is here |
| `edit/beats.py` | reads the song (beats, hits, sections) so cuts snap to it |
| `edit/wanted.json`, `edit/WANTED.md` | the news clips the edit has slots for, and a prompt for an agent to fetch them |
| `tools/fetch_wanted.py` | fetches the song and those clips (yt-dlp; finds each moment in the captions) |
| `edit/picks.tsv` | 154 Creative Commons clips chosen from YFCC100M, with notes |
| `edit/credits_yfcc.tsv` | author, title, licence and source for every one of them |
| `tools/yfcc/` | how the footage was found: a scanner that streamed YFCC100M's 65 GB metadata into a searchable index, then contact sheets |
| `tools/sat/` | satellite imagery: NOAA GOES-19 full-disk Earth, ESA Sentinel-2 true colour |

## finishing it: the song and the news clips

The cloud sandbox this was made in can't reach SoundCloud, YouTube or news sites. So the draft uses a temporary score,
and every news slot plays a stand-in, with the words typed out for dialogue clips.

1. On a computer with normal internet, run `python tools/fetch_wanted.py`. `edit/WANTED.md` has a prompt you can paste
   into an agent. It saves the song to `music/i-feel-weird.mp3` and the clips to `footage/news/`. Commit both and push.
2. Run `./make.sh music/i-feel-weird.mp3`.

That analyses the song, snaps every cut to its beats, drops each clip into its slot (cut on the words, subtitled),
turns the music down under speech, and writes `out/seize-the-future.mp4`. It's also worth re-timing the words by ear so
they sit in the gaps between vocal lines. They're all in `TEXT` at the bottom of `edit/timeline.py`.

Without a song, `./make.sh` rebuilds the draft with the temporary score.
Rebuilding needs the footage and satellite frames: `tools/yfcc/fetch_picks.py` and `tools/sat/*.py` re-download them.
Setup is `apt install ffmpeg` and `pip install numpy opencv-python-headless pillow librosa rasterio pyproj h5py`.

## where everything comes from

- **Footage:** YFCC100M via the Multimedia Commons (AWS Open Data), Flickr videos from 2004 to 2014 shared under Creative Commons.
  Only Attribution, Attribution-ShareAlike and NonCommercial variants are used. NoDerivatives licences are excluded because they forbid remixing.
  Every clip's author and licence is in `edit/credits_yfcc.tsv`. Credit them (a link in bio works). Because some clips are ShareAlike or NonCommercial, keep the piece non-commercial and share it under CC BY-NC-SA.
- **Earth:** NOAA GOES-19 ABI, full disk, Sept 29 2026 (US government work, public domain).
- **Ground:** contains modified Copernicus Sentinel data 2026 (ESA): Washington DC on Sept 16, Abilene TX on Sept 15.
- **Symbol:** the One World Flag by Thomas Mandl (2016), public domain.
- **News clips:** each one's source, channel and date is saved next to it in `footage/news/<id>.json`. Credit them in the caption.
- **Words on screen, verified before use:**
  - The richest 1% own 43.8% of the world's wealth, and the poorer half own 0.52% (Oxfam, *Resisting the Rule of the Rich*, Jan 19 2026).
  - Doomsday Clock set to 85 seconds to midnight on Jan 27 2026, the closest ever (Bulletin of the Atomic Scientists).
  - "SI instead of AI… You know what that means? 'Super'": President Trump at the White House on Sept 29 2026, after signing an order that federal agencies call AI "Super Intelligence" (CNBC, whitehouse.gov). The same day, AI CEOs signed a voluntary accord to "self-police".
  - "They are racing straight to self-improving superintelligence and gambling with our lives": Jacob Coxon, resigning from Anthropic on Sept 9 2026 (widely reported).
