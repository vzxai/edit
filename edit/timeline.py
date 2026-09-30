"""The edit, shot by shot. Seconds are nominal until the song is in; render.py can snap cuts to its beats.

Movements
  0  you are here            a dot in the dark becomes the planet
  I  i feel weird            the meaning crisis: screens, crowds, conveyor belts, spectacle, billionaires in space
  II their plan is to leave  end-times: the oligarchs, the hesitation, walls, cameras, masks, fire, ice, rockets
  III super                  the machine: data centres from orbit, the warning, the White House on Sept 29 2026
  IV there is no leaving     one world, one day, the children
  V  seize the future        the masses take power: Nepal, Sri Lanka, Bangladesh, Serbia; lanterns become dots

news(...) slots play footage/news/<id>.mp4 once tools/fetch_wanted.py has fetched it (see edit/wanted.json).
Until then each slot plays its fallback; dialogue slots type their words out over it instead.
"""

# clip(photoid, in_seconds, duration, **options): Creative Commons footage from YFCC100M
def clip(pid, t_in, dur, grade=None, fit="window", zoom=(1.0, 1.06), audio=0.0, speed=1.0, fx=(), width=1080, cy=880):
    return dict(kind="clip", pid=pid, t_in=t_in, dur=dur, grade=grade, fit=fit, zoom=zoom, audio=audio,
                speed=speed, fx=list(fx), width=width, cy=cy)

# news(id, duration, ...): fetched footage. quote = what is said (burned in as subtitles), either one
# string or [(line, seconds_into_shot), ...]; who = the speaker, the occasion and the date.
# t_in: seconds into the fetched file; None = just before the phrase (dialogue) or a third of the way in.
def news(nid, dur, t_in=None, audio=0.35, quote=None, who=None, fallback=None, grade=None, width=1080, cy=880,
         zoom=(1.0, 1.04)):
    return dict(kind="news", id=nid, dur=dur, t_in=t_in, audio=audio, quote=quote, who=who, fallback=fallback,
                grade=grade, fit="window", width=width, cy=cy, zoom=zoom, fx=[], speed=1.0)

def special(name, dur, **kw):
    return dict(kind=name, dur=dur, **kw)

SHOTS = []
def section(grade, items):
    for s in items:
        if s.get("grade") is None:
            s["grade"] = grade
        fb = s.get("fallback")
        if fb is not None:
            fb["dur"] = s["dur"]
            if fb.get("grade") is None:
                fb["grade"] = s["grade"]
        SHOTS.append(s)

# 0 ---------------------------------------------------------------- you are here
section("raw", [
    special("opening", 9.0),
])

# I ---------------------------------------------------------------- i feel weird
section("I", [
    clip(4405279512, 6.0, 2.5, fx=[("marker", 0.58, 0.62, 0.5)]),   # commuter crush from above; one of them is you
    clip(5278933106, 22.0, 1.2),                                    # escalator, vertical
    news("robot_marathon", 1.5, fallback=clip(4362591336, 7.0, 0)),
    clip(8214866621, 12.0, 1.5, audio=0.5),                         # election spectacle under the screens
    clip(6935544913, 13.0, 1.5),                                    # a baby lit by the TV
    news("zuck_friends", 4.5, audio=1.0,
         quote="“the average american, i think, has fewer than three friends.”",
         who="mark zuckerberg, on AI friends · dwarkesh podcast · april 2025",
         fallback=clip(12546612644, 30.0, 0)),                      # alone with the TV
    clip(7374162260, 41.0, 1.5),                                    # sharks in a shopping mall
    clip(4816384100, 7.0, 1.2),                                     # donut conveyor
    clip(8546876695, 14.0, 1.3),                                    # shift change, Shenzhen
    news("friend_ads", 1.8, fallback=clip(5765349125, 16.0, 0)),
    news("perry_kiss", 1.5, fallback=clip(5002819235, 9.0, 0)),
    news("bezos_paid", 4.0, audio=1.0,
         quote="“…every amazon employee and every amazon customer, because you guys paid for all this.”",
         who="jeff bezos, back from space · july 2021",
         fallback=clip(6268503929, 3.0, 0)),
    news("musk_chainsaw", 1.3, fallback=clip(5058934269, 11.0, 0)),
    clip(3063634893, 21.0, 1.5),                                    # neon through rain
    clip(4698724639, 12.0, 1.5),                                    # a kid in a car seat, looking out
    clip(2874922508, 46.0, 2.7),                                    # night drive
])

# II --------------------------------------------------------------- their plan is to leave
section("II", [
    news("inauguration_ceos", 2.2, fallback=clip(6198076084, 52.0, 0)),
    clip(9654010649, 12.0, 1.2),                                    # a parade on a TV on a wall
    clip(9654018151, 0.5, 1.0),                                     # missile truck
    news("thiel_endure", 7.5, audio=1.0,
         quote=[("“you would prefer the human race to endure, right?”", 0.0), ("“uh—”", 3.0),
                ("“you're hesitating.”", 5.0)],
         who="peter thiel, asked by ross douthat · nyt · june 2025",
         fallback=clip(2659993604, 1.0, 0)),                        # wall of cameras
    clip(2659993604, 6.0, 1.0),                                     # wall of cameras
    news("karp_kill", 4.0, audio=1.0,
         quote="“…to scare our enemies and, on occasion, kill them.”",
         who="alex karp, palantir ceo, to shareholders · feb 2025",
         fallback=clip(6349408051, 8.0, 0)),                        # police watchtower
    news("ice_masked", 1.5, fallback=clip(5562109516, 14.0, 0, audio=0.4)),
    clip(4777752861, 11.0, 1.5, audio=0.5),                         # she walks through the line
    news("la_fire", 1.5, fallback=clip(3540395513, 9.0, 0)),
    clip(6766537533, 13.0, 1.0),                                    # smoke over the horizon
    clip(4940777372, 40.0, 1.8, audio=0.6),                         # the glacier falls
    clip(5867249767, 50.0, 1.2),                                    # dosimeter
    clip(3772095704, 80.0, 1.3),                                    # Pripyat
    clip(4340515506, 7.0, 4.0, audio=0.7, zoom=(1.0, 1.12)),        # night launch: their plan is to leave
    clip(12954705905, 13.0, 0.8),                                   # contrail
])

# III -------------------------------------------------------------- super
section("III", [
    clip(5486920308, 2.0, 1.0),                                     # blinking servers
    news("stargate_announce", 2.0, audio=0.6, fallback=clip(9473414609, 2.0, 0)),
    special("sat_zoom", 3.0, still="s2/stargate_abilene_20260915.png", vis=(1400, 160), grade="sat",
            caption="abilene, texas · a stargate AI data centre\nsentinel-2 · sept 15 2026"),
    news("hinton_nobel", 4.5, audio=1.0,
         quote="“we urgently need research on how to prevent these new beings from wanting to take control.”",
         who="geoffrey hinton, at the nobel banquet · dec 2024",
         fallback=clip(6455164539, 21.0, 0, audio=0.35)),           # a child and a machine
    special("whitehouse", 3.5, grade="sat"),                        # orbit -> the White House, Sept 29 2026
    news("trump_si", 4.5, audio=1.0,
         quote="“SI instead of AI… you know what that means? super.”",
         who="the president, after signing an order renaming AI “super intelligence” · sept 29 2026",
         fallback=special("wh_hold", 0, grade="sat")),
    news("trump_selfpolice", 2.5, audio=1.0,
         quote="“i think i'm seeing tremendous self-policing.”",
         who="the president, on the AI companies · sept 29 2026",
         fallback=clip(13948922441, 2.0, 0)),                       # the board glitches
    news("huang_zero", 3.0, audio=1.0,
         quote="“there is zero percent chance that's going to be the end of the world.”",
         who="jensen huang, nvidia ceo, to cbs news · sept 2026",
         fallback=clip(9176269795, 32.0, 0)),                       # a face in the glitch
    special("quote", 4.0, bg=5486920308),                           # Coxon, from inside
])

# IV --------------------------------------------------------------- there is no leaving
section("IV", [
    special("earth_day", 4.0),
    clip(12186967753, 80.0, 2.0, fit="window", width=980),          # the sky as a sphere
    clip(5657225404, 50.0, 1.5),                                    # edge of the sky
    clip(3524650222, 5.0, 1.5, audio=0.7),                          # laughter
    clip(5314533385, 52.0, 1.5),                                    # holding hands
    clip(2654317769, 2.0, 1.5),                                     # kids running
])

# V ---------------------------------------------------------------- seize the future
section("V", [
    news("nepal_genz", 1.6, audio=0.6, fallback=clip(5945562365, 12.0, 0, audio=0.6)),
    news("srilanka_palace", 1.6, audio=0.5, fallback=clip(5946149468, 12.0, 0)),
    news("bangladesh_aug5", 1.6, audio=0.6, fallback=clip(4578194188, 8.0, 0)),
    news("onepiece_world", 1.3, fallback=clip(5891655482, 12.0, 0, audio=0.5)),
    news("serbia_silence", 1.6, fallback=clip(4159904558, 20.0, 0)),
    clip(6310970027, 1.0, 1.0, audio=0.5),                          # oakland general strike, 2011
    clip(5528754752, 8.0, 1.1, audio=0.5),                          # held up by hands
    news("nepal_cleanup", 1.4, fallback=clip(3006833942, 3.0, 0, audio=0.7)),
    clip(8353736337, 53.6, 2.0, fx=[("dots", 0.8)]),                # murmuration over the offices
    clip(8669531576, 21.0, 2.5, fx=[("rising_dots", 0.3)], audio=0.4),  # lanterns become dots
    clip(4162321413, 2.0, 1.3),                                     # a field of blue lights
    clip(11190993433, 2.5, 1.3),                                    # sunrise
    special("finale", 6.8),
])

# words: (start, end, text, style, size, y, mode)
# conservative on purpose. facts in mono with their source; feelings in serif.
TEXT = [
    (0.5, 5.0, "you are here.", "serif", 66, 1160, "fade"),
    (34.4, 36.9, "you're not broken.", "serif", 64, 1420, "fade"),
    (36.9, 39.8, "you're paying attention.", "serif", 64, 1420, "fade"),
    (40.2, 44.3, "1% of us own 43.8% of the world's wealth.", "mono-r", 44, 1400, "type"),
    (41.4, 44.3, "the poorer half owns 0.52% · oxfam · jan 2026", "mono", 24, 1470, "fade"),
    (64.3, 66.6, "85 seconds to midnight.", "mono-r", 50, 1400, "type"),
    (64.7, 66.6, "doomsday clock · jan 27 2026 · the closest it has ever been", "mono", 24, 1470, "fade"),
    (66.9, 70.6, "their plan for the end of the world\nis to leave.", "serif", 62, 1440, "fade"),
    (100.2, 103.4, "there is no leaving.", "serif", 64, 1560, "fade"),
    (107.2, 111.3, "there is only here,\nand each other.", "serif", 60, 1420, "fade"),
    (113.3, 116.6, "they have the money.\nwe have the numbers.", "serif", 62, 1440, "fade"),
    (125.0, 127.0, "it has never taken everyone.", "serif", 60, 1420, "fade"),
    (127.0, 129.8, "only enough of us, together, at once.", "serif", 60, 1420, "fade"),
]

def total():
    return sum(s["dur"] for s in SHOTS)

def apply_beats(path, tol=0.18):
    """snap every cut to the nearest beat of the song (and carry the words along with the pictures)"""
    import json
    import numpy as np
    info = json.load(open(path))
    grid = sorted(set(info["beats"] + info.get("hits", [])))
    nominal = [0.0]
    for s in SHOTS:
        nominal.append(nominal[-1] + s["dur"])
    snapped = [0.0]
    for b in nominal[1:-1]:
        g = np.asarray(grid)
        i = int(np.argmin(np.abs(g - b)))
        nb = float(g[i]) if abs(g[i] - b) <= tol else b
        snapped.append(max(nb, snapped[-1] + 0.4))
    snapped.append(max(nominal[-1], info["duration"]) if info.get("duration") else nominal[-1])
    for s, a, b in zip(SHOTS, snapped[:-1], snapped[1:]):
        s["dur"] = b - a
        if s.get("fallback") is not None:
            s["fallback"]["dur"] = s["dur"]
    for k, (t0, t1, *rest) in enumerate(TEXT):
        TEXT[k] = (float(np.interp(t0, nominal, snapped)), float(np.interp(t1, nominal, snapped)), *rest)
    return snapped
