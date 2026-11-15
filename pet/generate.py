#!/usr/bin/env python3
"""GitHub streak chicken: an animated pixel-art pet that grows with your contribution streak.

Writes pet/chicken.svg (640x360, 16:9) and keeps your record in pet/state.json.

Story:  Egg > Chick (1) > Rooster (10) > Phoenix (40) > finds a wife (55) > nest (65)
        > chicks (80) > 3rd chick (100) > chicks grow up (140) > the gang (200) > legendary (365)
A broken streak is a hard reset to the egg; your best streak stays on the card.

Usage:
    python pet/generate.py                     # fetch streak (env GH_TOKEN, GH_USER), update state
    python pet/generate.py --streak 85         # render one streak for testing (state untouched)
    python pet/generate.py --streak 0 --best 150
    python pet/generate.py --all               # preview every stage into pet/preview/
"""
import argparse, datetime as dt, json, os, urllib.request

CELL = 10
W, H = 640, 360
GROUND = 264                      # y (px) the birds stand on
STATE_FILE = "pet/state.json"

ACCENT, BG, TITLE, DIM = "#ff7a45", "#1c0f0c", "#ffe08a", "#d9a88a"

PALETTE = {
    "K": "#8a5428", "Y": "#ffd23f", "y": "#d49a12", "A": "#ffb020", "Q": "#e08a1e",
    "P": "#ff8fa3", "E": "#1b1b1b", "H": "#ffffff", "W": "#fff6e5", "g": "#e6cfa8",
    "L": "#ffe2b0", "R": "#e5484d", "r": "#a82a30", "S": "#14141c", "F": "#ff6a2b",
    "q": "#2fb5a8", "V": "#8a5cf6", "v": "#5b32b8", "D": "#c9701f", "O": "#f2a23c",
    "u": "#c98b45", "x": "#8a5a24",
}
PAL_ROOSTER = {"W": "#d9742e", "g": "#a14a1b", "L": "#f6c98a", "q": "#2fb5a8"}
PAL_PHOENIX = {"W": "#ff8a2a", "g": "#ffd23f", "L": "#ffe08a", "q": "#ff5a1f", "K": "#a63a14",
               "V": "#ff6a2b", "v": "#ffd23f", "R": "#ff3b30"}
PAL_GOLD = {"W": "#ffd23f", "g": "#ffb020", "L": "#fff1a8", "q": "#ffb347", "K": "#8a5a1a",
            "V": "#ffe066", "v": "#ff9f1c", "R": "#ff3b30"}
PAL_EGG = {"W": "#f3dcb8", "O": "#d79a5a", "D": "#a56a35"}

# (min_streak, title)
STAGES = [
    (0, "EGG"), (1, "CHICK"), (10, "ROOSTER"), (40, "PHOENIX"), (55, "THE COUPLE"),
    (65, "THE NEST"), (80, "NEW CHICKS"), (100, "FAMILY"), (140, "GROWING UP"),
    (200, "THE GANG"), (365, "LEGENDARY GANG"),
]


# ------------------------------------------------------------------ sprites
def mirror(half):
    for r in half:
        assert len(r) == 10, f"bad row length {len(r)}: {r!r}"
    return ["".join(r) + "".join(reversed(r)) for r in half]


EGG_HALF = [
    "....KK", "..KKWW", ".KWWWW", ".KWOOW", "KWWOOW", "KWWWWW", "KWWWDW",
    "KWWWWD", "KWOOWW", "KWOOWW", ".KWWWW", ".KWWWW", "..KKWW", "....KK",
]
EGG = ["".join(r) + "".join(reversed(r)) for r in EGG_HALF]       # 12 wide, 14 tall

CHICK = mirror([
    ".........K", "........KY", "....KKKKYY", "...KYYYYYY", "..KYYYYYYY",
    ".KYYYYYYYY", ".KYYEYYYYY", ".KYPEYYYAA", ".KYYYYYYYA", ".KYYYYYYYY",
    ".KyYYYYYYY", ".KyyYYYYYY", "..KyYYYYYY", "..KKYYYYYY", "...KKKKKKK",
    "....QQ....", "...QQQ....",
])
HEN = mirror([
    ".......R.R", ".......RRR", "...KKKKRRR", "..KWWWWWWW", ".KWWWWWWWW",
    ".KWWWWWWWW", ".KWWEWWWWW", ".KWWEWWWAA", ".KWWWWWWWA", ".KWWWWWWWR",
    ".KWWWWWWWR", ".KWWWWWWWW", "KWWWWWWWWW", "KWggWWLLLL", "KWgggWLLLL",
    "KWgggWLLLL", "KWWggWLLLL", ".KWWWWWWWW", "..KKKKKKKK", "....QQ....",
    "...QQQ....",
])
BOW = ["..PP.PP.............", "..PPRPP............."]
SHADES = ["...SSSS......SSSS...", "..SSSSSSSSSSSSSSSS..", "...SHSS......SSHS..."]   # y=5
SCARF = ["..RRRRRRRRRRRRRRRR..", "..rrrrrrrrrrrrrrrr..",
         ".........RR.........", ".........Rr........."]                                  # y=12
FAN = ["K....", "KqK..", "KqqK.", "KqYqK", "KqqqK", "KqYqK", ".KqqK", "..KKK"]
FLAME = ["..........F.........", ".........FFF.F......", "........FFYYFFF....."]
WING = ["v......", "vv.....", "vVv....", "vVVv...", "vVVVvv.", ".vVVVVv", "..vvvvv"]
CROWN = ["......Y..YY..Y......", "......YYYYYYYY......", "......YyYyyYyY......"]
NEST = ["..KKKKKKKKKKKK..", ".KuuuuuuuuuuuuK.", "KuuxuuuuxuuuuxuK",
        "KuuuuxuuuuuxuuuK", ".KuuuuuuuuuuuuK.", "..KKKKKKKKKKKK.."]
HEART = [".PP.PP.", "PPPPPPP", "PPPPPPP", ".PPPPP.", "..PPP..", "...P..."]


def px(grid, ox=0, oy=0, only=None):
    return [(x + ox, y + oy, ch)
            for y, row in enumerate(grid) for x, ch in enumerate(row)
            if ch != "." and (only is None or ch in only)]


def rects(pixels, pal):
    return "".join(
        f'<rect x="{x * CELL}" y="{y * CELL}" width="{CELL}" height="{CELL}" fill="{pal[c]}"/>'
        for x, y, c in pixels)


def L(grid, x, y, pal, cls=None, only=None):
    return (f'<g class="{cls}">' if cls else "<g>") + rects(px(grid, x, y, only), pal) + "</g>"


def flip(grid):
    return [r[::-1] for r in grid]


# ------------------------------------------------------------------ figures
def bird(kind, crown=False):
    """Return (svg parts, sprite rows, shadow half-width in px at scale 1)."""
    pal = {**PALETTE}
    if kind == "chick":
        return (L(CHICK, 0, 0, pal, only=set("KYyAPQ")) + L(CHICK, 0, 0, pal, "eyes", only="E"), 17, 52)
    if kind in ("hen", "teen_hen"):
        parts = L(HEN, 0, 0, pal, only=set("KWgLRAQ")) + L(HEN, 0, 0, pal, "eyes", only="E")
        if kind == "hen":
            parts += L(BOW, 0, 1, pal)
        return parts, 21, 62
    pal = {**PALETTE, **{"rooster": PAL_ROOSTER, "teen_rooster": PAL_ROOSTER,
                         "phoenix": PAL_PHOENIX, "golden": PAL_GOLD}[kind]}
    fiery = kind in ("phoenix", "golden")
    p = []
    if fiery:
        p.append(L(WING, -4, 4, pal, "wingL"))
        p.append(L(flip(WING), 17, 4, pal, "wingR"))
    if kind != "teen_rooster":
        p.append(L(FAN, -3, 5, pal)); p.append(L(flip(FAN), 18, 5, pal))
    p.append(L(HEN, 0, 0, pal, only=set("KWgLRAQ")))
    if kind == "teen_rooster":
        p.append(L(HEN, 0, 0, pal, "eyes", only="E"))
    else:
        p.append(L(SHADES, 0, 5, pal)); p.append(L(SCARF, 0, 12, pal))
    if crown:
        p.append(L(CROWN, 0, -1, pal))
    elif fiery:
        p.append(L(FLAME, 0, -1, pal))
    return "".join(p), 21, 62


def place(kind, cx, s, delay=0.0, crown=False):
    parts, rows, rx = bird(kind, crown)
    tx, ty = cx - 100 * s, GROUND - rows * CELL * s
    return (f'<ellipse cx="{cx}" cy="{GROUND + 2}" rx="{rx * s:.1f}" ry="{6 * s + 2:.1f}" fill="#000" opacity=".4"/>'
            f'<g transform="translate({tx:.1f},{ty:.1f}) scale({s})">'
            f'<g class="bob" style="animation-delay:{delay}s">{parts}</g></g>')


def egg(cx, s, ground=GROUND, wobble=True, delay=0.0):
    pal = {**PALETTE, **PAL_EGG}
    tx, ty = cx - 60 * s, ground - 14 * CELL * s
    cls = "wobble" if wobble else ""
    return (f'<g transform="translate({tx:.1f},{ty:.1f}) scale({s})">'
            f'<g class="{cls}" style="animation-delay:{delay}s">{rects(px(EGG), pal)}</g></g>')


def egg_shadow(cx, s):
    return f'<ellipse cx="{cx}" cy="{GROUND + 2}" rx="{45 * s:.1f}" ry="{6 * s + 2:.1f}" fill="#000" opacity=".4"/>'


def nest(cx):
    s = 0.7
    pal = {**PALETTE}
    base = GROUND - 6 * CELL * s
    eggs = egg(cx - 24, 0.45, ground=base + 22, delay=0) + egg(cx + 24, 0.45, ground=base + 22, delay=.5)
    body = f'<g transform="translate({cx - 8 * CELL * s:.1f},{base:.1f}) scale({s})">{rects(px(NEST), pal)}</g>'
    return (f'<ellipse cx="{cx}" cy="{GROUND + 2}" rx="{60}" ry="6" fill="#000" opacity=".4"/>' + eggs + body)


def heart(cx, y, delay):
    pal = {**PALETTE}
    return (f'<g transform="translate({cx - 21},{y})"><g class="heart" style="animation-delay:{delay}s">'
            f'<g transform="scale(.6)">{rects(px(HEART), pal)}</g></g></g>')


def scene(stage):
    if stage == 0:
        return egg_shadow(320, 1.3) + egg(320, 1.3)
    if stage == 1:
        return place("chick", 320, 1.1)
    if stage == 2:
        return place("rooster", 320, 1.0)
    if stage == 3:
        return place("phoenix", 320, 0.95)
    if stage == 4:
        return (place("phoenix", 205, .85) + place("hen", 440, .8, .3)
                + heart(330, 130, 0) + heart(355, 150, 1.0) + heart(305, 160, 1.7))
    parents = place("phoenix", 118, .7) + place("hen", 520, .72, .3)
    if stage == 5:
        return parents + nest(320)
    if stage == 6:
        return parents + place("chick", 280, .5, .1) + place("chick", 360, .5, .5)
    if stage == 7:
        return (parents + place("chick", 247, .45, .1) + place("chick", 320, .45, .5)
                + place("chick", 393, .45, .9))
    if stage == 8:
        return (parents + place("teen_rooster", 247, .42, .1) + place("teen_hen", 320, .42, .5)
                + place("teen_rooster", 393, .42, .9))
    kind = "phoenix" if stage == 9 else "golden"
    side = "rooster" if stage == 9 else "golden"
    return (place(side, 125, .75, .2) + place(kind, 515, .75, .6)
            + place(kind, 320, .95, 0, crown=(stage == 10)))


# ------------------------------------------------------------------ card
def stage_for(streak):
    return max(i for i, s in enumerate(STAGES) if streak >= s[0])


def days(n):
    return f"{n} DAY{'S' if n != 1 else ''}"


def sparkles(stage):
    if stage < 3:
        return ""
    spots = [(45, 110), (595, 100), (40, 215), (600, 215), (320, 78)][: 2 + stage // 3 + (1 if stage >= 9 else 0)]
    out = ""
    for i, (x, y) in enumerate(spots):
        def r(dx, dy, o):
            return f'<rect x="{x + dx * 8}" y="{y + dy * 8}" width="8" height="8" fill="#ffb347" opacity="{o}"/>'
        out += (f'<g class="spark" style="animation-delay:{i * .4}s">'
                + r(0, 0, 1) + r(-1, 0, .5) + r(1, 0, .5) + r(0, -1, .5) + r(0, 1, .5) + "</g>")
    return out


def ground_strip():
    tufts = "".join(
        f'<rect x="{x}" y="{GROUND + 8}" width="4" height="4" fill="#3f6b2a"/>'
        f'<rect x="{x + 6}" y="{GROUND + 10}" width="4" height="2" fill="#2d5220"/>'
        for x in range(30, 620, 46))
    return f'<rect x="14" y="{GROUND + 12}" width="{W - 28}" height="6" fill="#2a1a12"/>' + tufts


def hud(streak, best, stage):
    lo = STAGES[stage][0]
    nxt = STAGES[stage + 1] if stage + 1 < len(STAGES) else None
    segs, x0, bw = 20, 30, 400
    if nxt is None:
        filled, label = segs, "MAX LEVEL REACHED"
    else:
        filled = int(segs * (streak - lo) / (nxt[0] - lo))
        label = f"{days(nxt[0] - streak)} TO {nxt[1]}"
    sw = bw / segs
    bar = "".join(
        f'<rect x="{x0 + i * sw + 1:.1f}" y="306" width="{sw - 2:.1f}" height="12" '
        f'fill="{ACCENT if i < filled else "#2c2433"}"/>' for i in range(segs))
    if streak == 0:
        msg = "STREAK BROKE! COMMIT TO HATCH" if best > 0 else "COMMIT TODAY TO HATCH ME"
    else:
        msg = f"{streak}-DAY STREAK"
    live = streak > 0 and streak >= best
    return (f'<text x="{x0}" y="296" class="sm">{msg}</text>{bar}'
            f'<text x="{x0}" y="338" class="sm">{label}</text>'
            f'<rect x="470" y="288" width="140" height="56" rx="6" fill="#26140f" stroke="{ACCENT}" stroke-width="2"/>'
            f'<text x="540" y="308" text-anchor="middle" class="sm">{"PERSONAL BEST" if live else "BEST STREAK"}</text>'
            f'<text x="540" y="332" text-anchor="middle" class="best">{days(best)}</text>')


CSS = (
    "text{font-family:'Courier New',monospace;font-weight:bold;letter-spacing:1px}"
    f".t{{font-size:22px;fill:{TITLE}}}.d{{font-size:20px;fill:{ACCENT}}}"
    f".sm{{font-size:12px;fill:{DIM}}}.best{{font-size:16px;fill:{TITLE}}}"
    ".bob{animation:bob 1.2s steps(1,end) infinite}"
    "@keyframes bob{0%{transform:translateY(0)}50%{transform:translateY(-5px)}}"
    ".wobble{transform-box:fill-box;transform-origin:50% 100%;animation:wob 2s ease-in-out infinite}"
    "@keyframes wob{0%,55%,100%{transform:rotate(0)}65%{transform:rotate(-7deg)}80%{transform:rotate(7deg)}}"
    ".eyes{transform-box:fill-box;transform-origin:center;animation:blink 4s infinite}"
    "@keyframes blink{0%,92%,100%{transform:scaleY(1)}95%{transform:scaleY(.1)}}"
    ".wingL{transform-box:fill-box;transform-origin:100% 100%;animation:fl 1s ease-in-out infinite}"
    ".wingR{transform-box:fill-box;transform-origin:0 100%;animation:fr 1s ease-in-out infinite}"
    "@keyframes fl{0%,100%{transform:rotate(0)}50%{transform:rotate(-12deg)}}"
    "@keyframes fr{0%,100%{transform:rotate(0)}50%{transform:rotate(12deg)}}"
    ".spark{animation:tw 1.6s ease-in-out infinite}"
    "@keyframes tw{0%,100%{opacity:0}50%{opacity:1}}"
    ".heart{animation:hv 2.4s ease-in-out infinite;opacity:0}"
    "@keyframes hv{0%{transform:translateY(0);opacity:0}30%{opacity:1}100%{transform:translateY(-34px);opacity:0}}"
)


def render(streak, best=None):
    best = streak if best is None else max(best, streak)
    stage = stage_for(streak)
    return f'''<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}">
<style>{CSS}</style>
<rect x="2" y="2" width="{W - 4}" height="{H - 4}" rx="12" fill="{BG}" stroke="{ACCENT}" stroke-width="3"/>
<rect x="9" y="9" width="{W - 18}" height="{H - 18}" rx="7" fill="none" stroke="#2c2433" stroke-width="2" stroke-dasharray="4 4"/>
<text x="30" y="36" class="t">{STAGES[stage][1]}</text>
<text x="{W - 30}" y="36" text-anchor="end" class="d">DAY {streak}</text>
{sparkles(stage)}{ground_strip()}{scene(stage)}{hud(streak, best, stage)}
</svg>'''


# ------------------------------------------------------------------ streak + record
QUERY = ("query($u:String!,$f:DateTime!,$t:DateTime!){user(login:$u){"
         "contributionsCollection(from:$f,to:$t){contributionCalendar{weeks{"
         "contributionDays{date contributionCount}}}}}}")


def fetch_counts(user, token, start, end):
    body = json.dumps({"query": QUERY, "variables": {
        "u": user, "f": f"{start}T00:00:00Z", "t": f"{end}T23:59:59Z"}}).encode()
    req = urllib.request.Request("https://api.github.com/graphql", body, {
        "Authorization": f"bearer {token}", "Content-Type": "application/json"})
    data = json.load(urllib.request.urlopen(req))
    weeks = data["data"]["user"]["contributionsCollection"]["contributionCalendar"]["weeks"]
    return {d["date"]: d["contributionCount"] for w in weeks for d in w["contributionDays"]}


def fetch_streak(user, token):
    """Consecutive days with >=1 contribution, ending today (or yesterday if today is empty)."""
    today = dt.datetime.now(dt.timezone.utc).date()
    counts, end = {}, today
    for _ in range(4):                      # API caps one query at a year; look back up to ~4 years
        start = end - dt.timedelta(days=364)
        counts.update(fetch_counts(user, token, start, end))
        if any(c == 0 for d, c in counts.items() if d < str(today)):
            break                           # found a gap, no need to go further back
        end = start - dt.timedelta(days=1)
    day = today if counts.get(str(today), 0) else today - dt.timedelta(days=1)
    streak = 0
    while counts.get(str(day), 0) > 0:
        streak += 1
        day -= dt.timedelta(days=1)
    return streak


def load_best():
    try:
        return int(json.load(open(STATE_FILE))["best"])
    except (OSError, ValueError, KeyError):
        return 0


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--streak", type=int, help="render this streak (testing; state file untouched)")
    ap.add_argument("--best", type=int, default=None)
    ap.add_argument("--all", action="store_true", help="write a preview of every stage")
    ap.add_argument("--out", default="pet/chicken.svg")
    a = ap.parse_args()
    if a.all:
        os.makedirs("pet/preview", exist_ok=True)
        for i, (lo, name) in enumerate(STAGES):
            s = lo
            best = 150 if lo == 0 else s
            open(f"pet/preview/{i:02d}_{name.lower().replace(' ', '_')}.svg", "w").write(render(s, best))
    elif a.streak is not None:
        open(a.out, "w").write(render(a.streak, a.best))
    else:
        streak = fetch_streak(os.environ["GH_USER"], os.environ["GH_TOKEN"])
        best = max(load_best(), streak)
        os.makedirs(os.path.dirname(STATE_FILE), exist_ok=True)
        json.dump({"best": best}, open(STATE_FILE, "w"))
        open(a.out, "w").write(render(streak, best))
        print(f"streak={streak} best={best} stage={STAGES[stage_for(streak)][1]}")