"""The edit, shot by shot, cut to "i feel weird" by meat computer (141 BPM, 2:16).

  song                          edit
  0:00  intro        8 bars     you are here: a dot in the dark becomes the planet; one of the crowd is you
  0:13  verse       24 bars     i feel weird: screens, conveyor belts, spectacle; zuckerberg, bezos, musk, karp
  0:54  drop        16 bars     their plan is to leave: the oligarchs, masks, the machine, fire, ice, a launch
  1:21  breakdown    8 bars     thiel hesitates on whether the human race should endure; hinton's warning
  1:35  build        8 bars     the White House, Sept 29 2026: "super intelligent"; huang: "zero percent chance"
  1:47  (the song catches its breath)   the whole Earth: there is no leaving
  1:49  last chorus 15 bars     the masses take power: Nepal, Sri Lanka, Bangladesh, Peru, Serbia; lanterns become dots
  2:14  silence                 one nation. earth. seize the future. for all.

Every cut is on the song's beat grid. Shot lengths are counted in beats (b(n)), and each section starts
exactly where the song's does (measured from the audio: that is where the bass and hi-hats come and go).
news(...) slots play footage/news/<id>.mp4 (fetched by tools/fetch_wanted.py, see edit/wanted.json).
Without it a slot plays a Creative Commons stand-in, and dialogue slots type their words out over it instead.
"""

BPM = 141.0
BEAT = 60 / BPM
BAR = 4 * BEAT

def b(n):
    """n beats, in seconds"""
    return n * BEAT

# where the song's sections start (seconds)
INTRO, VERSE, DROP, BREAK, BUILD, FINAL, OUT, END = 0.0, 13.70, 54.57, 81.80, 95.42, 109.04, 134.56, 136.64

def at(start, beats):
    """the time `beats` beats after a section starts"""
    return start + beats * BEAT

def intro_bar(k):
    """downbeat k (0-8) of the intro"""
    return VERSE - (8 - k) * BAR

# clip(photoid, in_seconds, duration, **options): Creative Commons footage from YFCC100M
def clip(pid, t_in, dur, grade=None, fit="window", zoom=(1.0, 1.06), audio=0.0, speed=1.0, fx=(), width=1080, cy=880):
    return dict(kind="clip", pid=pid, t_in=t_in, dur=dur, grade=grade, fit=fit, zoom=zoom, audio=audio,
                speed=speed, fx=list(fx), width=width, cy=cy)

# news(id, duration, ...): fetched footage.
#   t_in   seconds into the fetched file (None = just before the phrase, or a third of the way in)
#   quote  what is said, burned in as subtitles: one string, or [(line, seconds_into_shot), ...]
#   who    the speaker, the occasion and the date (shown under the subtitles, or at who_y)
#   audio  the level of the clip's own sound (1 for a voice, 0.35 under the song otherwise)
#   speech the clip's own voice leads and the music steps back (default: when there is a quote)
#   duck   how far the music steps back under the voice; a_out: where in the file the voice should stop
#   zoom   (start, end) crop of the source; focus: where the crop sits (0-1, 0-1)
#   cover  [(x0, y0, x1, y1, t0, t1), ...] parts of the source frame to blur (0-1), between file times t0 and t1
def news(nid, dur, t_in=None, audio=None, quote=None, who=None, fallback=None, grade=None, width=1080, cy=880,
         zoom=(1.0, 1.04), focus=(0.5, 0.5), speech=None, duck=0.18, a_out=None, who_y=None, cover=()):
    speech = bool(quote) if speech is None else speech
    if audio is None:
        audio = 1.0 if speech else 0.35
    return dict(kind="news", id=nid, dur=dur, t_in=t_in, audio=audio, quote=quote, who=who, fallback=fallback,
                grade=grade, fit="window", width=width, cy=cy, zoom=zoom, focus=focus, fx=[], speed=1.0,
                speech=speech, duck=duck, a_out=a_out, who_y=who_y, cover=list(cover))

def special(name, dur, **kw):
    return dict(kind=name, dur=dur, **kw)

SHOTS = []

def total():
    return sum(s["dur"] for s in SHOTS)

def section(grade, until, items):
    """append a section's shots; the last one runs until the song's next section starts"""
    items[-1]["dur"] = until - total() - sum(s["dur"] for s in items[:-1])
    assert items[-1]["dur"] > 0.3, f"section before {until}s is overfull"
    for s in items:
        if s.get("grade") is None:
            s["grade"] = grade
        fb = s.get("fallback")
        if fb is not None:
            fb["dur"] = s["dur"]
            if fb.get("grade") is None:
                fb["grade"] = s["grade"]
        SHOTS.append(s)

# intro ------------------------------------------------------------ you are here
section("I", VERSE, [
    special("opening", intro_bar(4), grade="raw",
            pulses=[intro_bar(0), intro_bar(1), intro_bar(2)], grow=(intro_bar(2), intro_bar(3) + b(1.5))),
    clip(4405279512, 6.0, b(8), fx=[("marker", 0.58, 0.62, b(1))]),   # commuter crush from above; one of them is you
    clip(5278933106, 22.0, b(3)),                                   # escalator, vertical
    clip(8214866621, 12.0, b(3), audio=0.5),                        # election spectacle under the screens
    clip(6935544913, 13.0, 0),                                      # a baby lit by the TV
])

# verse ------------------------------------------------------------ i feel weird
section("I", DROP, [
    news("robot_marathon", b(4), t_in=26.5, fallback=clip(4362591336, 7.0, 0)),
    clip(12546612644, 32.0, b(3)),                                  # alone with the TV
    news("zuck_friends", b(12), t_in=0.8,
         quote=[("“the average american, i think, has—”", 0.0), ("“i think it's fewer than three friends.”", 2.8)],
         who="mark zuckerberg, on AI friends · dwarkesh podcast · april 2025",
         fallback=clip(12546612644, 30.0, 0)),
    clip(7374162260, 41.0, b(3)),                                   # sharks in a shopping mall
    clip(4816384100, 7.0, b(2)),                                    # donut conveyor
    clip(8546876695, 14.0, b(3)),                                   # shift change, Shenzhen
    clip(5765349125, 16.0, b(2)),                                   # empty cubicles
    news("friend_ads", b(4), t_in=0.6, fallback=clip(5765349125, 16.0, 0)),   # STOP PROFITING OFF OF LONELINESS
    clip(5002819235, 9.0, b(2)),                                    # a robot dances for a crowd
    clip(6268503929, 3.0, b(2)),                                    # billboard trucks, Tokyo
    news("perry_kiss", b(4), t_in=3.5, fallback=clip(5002819235, 9.0, 0)),
    news("bezos_paid", b(16), t_in=5.45,
         quote=[("“…every amazon employee\nand every amazon customer,”", 0.0),
                ("“because you guys\npaid for all of this.”", 3.85)],
         who="jeff bezos, back from space · july 2021",
         fallback=clip(6268503929, 3.0, 0)),
    clip(8644875894, 12.0, b(2)),                                   # a stretch hummer in times square
    news("musk_chainsaw", b(4), t_in=1.5, audio=0.6, zoom=(2.0, 2.2), focus=(0.28, 0.05),
         fallback=clip(5058934269, 11.0, 0)),                     # the chainsaw "for bureaucracy"
    news("karp_kill", b(10), t_in=4.0,
         quote=[("“and when it's necessary,\nto scare our enemies—”", 0.0), ("“and, on occasion,\nkill them.”", 3.05)],
         who="alex karp, palantir ceo · earnings call · feb 2025",
         fallback=clip(6349408051, 8.0, 0)),                        # police watchtower
    clip(3063634893, 21.0, b(3)),                                   # neon through rain
    clip(3741622921, 44.0, b(3)),                                   # a child alone in a hedge maze
    clip(4698724639, 12.0, b(4)),                                   # a kid in a car seat, looking out
    clip(2874922508, 46.0, 0),                                      # night drive
])

# drop ------------------------------------------------------------- their plan is to leave
section("II", BREAK, [
    news("inauguration_ceos", b(8), t_in=7.8, fallback=clip(6198076084, 52.0, 0)),
    clip(9654010649, 12.0, b(2)),                                   # a parade on a TV on a wall
    clip(9654018151, 0.5, b(2)),                                    # missile truck
    clip(2659993604, 6.0, b(2)),                                    # wall of cameras
    news("ice_masked", b(4), t_in=23.5, audio=0.4, fallback=clip(5562109516, 14.0, 0, audio=0.4)),
    clip(4777752861, 11.0, b(3), audio=0.5),                        # she walks through the line
    clip(5486920308, 2.0, b(2), grade="III"),                       # blinking servers
    news("stargate_announce", b(4), t_in=4.0, audio=0.5, grade="III", fallback=clip(9473414609, 2.0, 0)),
    special("sat_zoom", b(5), still="s2/stargate_abilene_20260915.png", vis=(1400, 160), grade="sat",
            caption="abilene, texas · a stargate AI data centre\nsentinel-2 · sept 15 2026"),
    news("la_fire", b(4), t_in=2.0, fallback=clip(3540395513, 9.0, 0)),
    clip(6766537533, 13.0, b(2)),                                   # smoke over the horizon
    clip(4940777372, 40.0, b(4), audio=0.6),                        # the glacier falls
    clip(5867249767, 50.0, b(3)),                                   # dosimeter
    clip(3772095704, 80.0, b(4)),                                   # Pripyat
    clip(4340515506, 7.0, b(8), audio=0.7, zoom=(1.0, 1.12)),       # night launch: their plan is to leave
    clip(12954705905, 13.0, 0),                                     # contrail
])

# breakdown -------------------------------------------------------- the hesitation
# the Thiel clip is vertical, with the NYT's own captions: it fills the frame and gets no subtitles of ours.
# the TikTok watermark on the repost is blurred out (it jumps from left to right at 4.9s).
section("III", BUILD, [
    news("thiel_endure", b(19), t_in=0.0, speech=True, duck=0.3, zoom=(1.0, 1.05), cy=960,
         who="peter thiel, asked by ross douthat · nyt opinion · june 2025", who_y=1800,
         cover=[(0.0, 0.43, 0.24, 0.57, 0.0, 5.0), (0.77, 0.73, 1.0, 0.87, 4.8, 99.0)],
         fallback=clip(2659993604, 1.0, 0)),
    news("hinton_nobel", 0, t_in=1.3, duck=0.3,
         quote=[("“we urgently need research\non how to prevent”", 0.1),
                ("“these new beings\nfrom wanting to take control.”", 3.14)],
         who="geoffrey hinton, at the nobel banquet · dec 2024",
         fallback=clip(6455164539, 21.0, 0, audio=0.35)),           # a child and a machine
])

# build ------------------------------------------------------------ super
section("III", FINAL, [
    special("whitehouse", b(4), grade="sat"),                       # orbit -> the White House, Sept 29 2026
    news("trump_si", b(10), t_in=9.47, a_out=13.52, duck=0.16,
         quote=[("“SI instead of AI.”", 0.0), ("“you know what that means?\nsuper intelligent.”", 1.6)],
         who="the president at the white house · sept 29 2026\nafter signing an order renaming AI “super intelligence”",
         fallback=special("wh_hold", 0, grade="sat")),
    news("huang_zero", b(15), t_in=1.58, duck=0.2,
         quote=[("“2030 is not going to be\nthe end of the world.”", 0.0),
                ("“there is zero percent chance that's\ngoing to be the end of the world.”", 3.1)],
         who="jensen huang, nvidia ceo, to cbs news · sept 2026",
         fallback=clip(9176269795, 32.0, 0)),                       # a face in the glitch
    special("earth_day", 0, grade="earth", span=(0.68, 0.72), push=20),   # the song stops for a breath: 16:20-17:00 UTC
])

# last chorus ------------------------------------------------------ seize the future
section("V", END, [
    news("nepal_genz", b(4), t_in=0.2, audio=0.6, fallback=clip(5945562365, 12.0, 0, audio=0.6)),
    news("srilanka_palace", b(4), t_in=1.8, audio=0.5, fallback=clip(5946149468, 12.0, 0)),
    news("bangladesh_aug5", b(6), t_in=70.0, audio=0.6, fallback=clip(4578194188, 8.0, 0)),
    news("onepiece_world", b(3), t_in=18.2, fallback=clip(5891655482, 12.0, 0, audio=0.5)),
    news("serbia_silence", b(4), t_in=3.0, fallback=clip(4159904558, 20.0, 0)),
    clip(6310970027, 1.0, b(3), audio=0.5),                         # oakland general strike, 2011
    clip(5528754752, 8.0, b(3), audio=0.5),                         # held up by hands
    news("nepal_cleanup", b(3), t_in=10.0, fallback=clip(3006833942, 3.0, 0, audio=0.7)),
    clip(8353736337, 53.6, b(6), fx=[("dots", 0.8)]),               # murmuration over the offices
    clip(8669531576, 21.0, b(8), fx=[("rising_dots", 0.3)], audio=0.4),   # lanterns become dots
    clip(4162321413, 2.0, b(3)),                                    # a field of blue lights
    clip(11190993433, 2.5, b(3)),                                   # sunrise
    special("finale", 0, grade="raw"),                              # the planet becomes the symbol
])
SHOTS[-1]["land"] = OUT - (END - SHOTS[-1]["dur"])                  # the words land when the music stops

# words: (start, end, text, style, size, y, mode)
# conservative on purpose. facts in mono with their source; feelings in serif.
TEXT = [
    (0.3, intro_bar(2) + 0.8, "you are here.", "serif", 66, 1160, "fade"),
    (at(VERSE, 80.2), at(VERSE, 85.8), "you're not broken.", "serif", 64, 1420, "fade"),
    (at(VERSE, 86.4), at(VERSE, 95.6), "you're paying attention.", "serif", 64, 1420, "fade"),
    (at(DROP, 1), at(DROP, 10.2), "1% of us own 43.8%\nof the world's wealth.", "mono-r", 46, 1390, "type"),
    (at(DROP, 4), at(DROP, 10.2), "the poorer half owns 0.52% · oxfam · jan 2026", "mono", 24, 1500, "fade"),
    (at(DROP, 42.3), at(DROP, 48.8), "85 seconds to midnight.", "mono-r", 50, 1400, "type"),
    (at(DROP, 43.3), at(DROP, 48.8), "doomsday clock · jan 27 2026 · the closest it has ever been", "mono", 24, 1470, "fade"),
    (at(DROP, 50), at(DROP, 60.5), "their plan for the end of the world\nis to leave.", "serif", 62, 1440, "fade"),
    (FINAL - b(3) + 0.12, at(FINAL, 3.8), "there is no leaving.", "serif", 64, 1560, "fade"),
    (at(FINAL, 8.3), at(FINAL, 17), "they have the money.\nwe have the numbers.", "serif", 62, 1440, "fade"),
    (at(FINAL, 30.4), at(FINAL, 35.8), "it has never taken everyone.", "serif", 60, 1420, "fade"),
    (at(FINAL, 36.3), at(FINAL, 43.8), "only enough of us,\ntogether, at once.", "serif", 60, 1420, "fade"),
]
