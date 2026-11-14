#!/usr/bin/env python3
"""GitHub streak chicken: an animated pixel-art pet that evolves with your contribution streak.

Writes pet/chicken.svg. Stages: Egg (0) > Chick (1) > Hen (7) > Rooster (30) > Phoenix (100).

Usage:
    python pet/generate.py              # fetch streak via GitHub API (env GH_TOKEN, GH_USER)
    python pet/generate.py --streak 42  # render a specific streak (testing)
    python pet/generate.py --all        # render every stage into pet/preview/
"""
import argparse, datetime as dt, json, os, urllib.request

CELL = 10
CW, CH = 32, 28          # canvas size in cells
OX = 6                   # sprite x offset (sprites are 20 cells wide)
GROUND = 26              # row the pets stand on

PALETTE = {
    "K": "#8a5428", "O": "#f2a23c", "D": "#c9701f", "L": "#ffe2b0",
    "P": "#ff8fa3", "E": "#1b1b1b", "H": "#ffffff", "W": "#fff6e5",
    "R": "#e5484d", "r": "#a82a30", "Y": "#ffd23f", "y": "#d49a12",
    "B": "#7cc4ff", "b": "#3f8fd8", "S": "#14141c",
    "A": "#ffb020", "Q": "#e08a1e", "g": "#e6cfa8", "F": "#ff6a2b", "N": "#6fcf6a",
    "n": "#2c7a3e", "M": "#d9f5a8", "T": "#f2e2a0", "V": "#8a5cf6", "v": "#5b32b8", "q": "#2fb5a8",
}

# ------------------------------------------------------------------ sprites
def mirror(half):
    for r in half:
        assert len(r) == 10, f"bad row length {len(r)}: {r!r}"
    return ["".join(r) + "".join(reversed(r)) for r in half]


EGG_HALF = [
    "....KK", "..KKWW", ".KWWWW", ".KWOOW", "KWWOOW", "KWWWWW", "KWWWDW",
    "KWWWWD", "KWOOWW", "KWOOWW", ".KWWWW", ".KWWWW", "..KKWW", "....KK",
]
EGG = ["".join(r) + "".join(reversed(r)) for r in EGG_HALF]   # 12 wide

# ---- chicken
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
HEN_SHADES = ["...SSSS......SSSS...", "..SSSSSSSSSSSSSSSS..", "...SHSS......SSHS..."]  # y=5
HEN_SCARF = ["..RRRRRRRRRRRRRRRR..", "..rrrrrrrrrrrrrrrr..",
             ".........RR.........", ".........Rr........."]  # y=12
FAN = ["K....", "KqK..", "KqqK.", "KqYqK", "KqqqK", "KqYqK", ".KqqK", "..KKK"]
FLAME = ["..........F.........", ".........FFF.F......", "........FFYYFFF....."]
WING_S = ["v......", "vv.....", "vVv....", "vVVv...", "vVVVvv.", ".vVVVVv", "..vvvvv"]

PAL_ROOSTER = {"W": "#d9742e", "g": "#a14a1b", "L": "#f6c98a", "q": "#2fb5a8"}
PAL_PHOENIX = {"W": "#ff8a2a", "g": "#ffd23f", "L": "#ffe08a", "q": "#ff5a1f", "K": "#a63a14",
               "V": "#ff6a2b", "v": "#ffd23f", "R": "#ff3b30"}
# ------------------------------------------------------------------ pets
PETS = {
    "chicken": dict(
        stages=[(0, "EGG", 1), (1, "CHICK", 7), (7, "HEN", 30), (30, "ROOSTER", 100), (100, "PHOENIX", None)],
        bg="#1c0f0c", accent="#ff7a45", title="#ffe08a", dim="#d9a88a", spark="#ffb347",
        egg={"W": "#f3dcb8", "O": "#d79a5a", "D": "#a56a35"}),
}


def px(grid, ox=0, oy=0, only=None):
    return [(x + ox, y + oy, ch)
            for y, row in enumerate(grid) for x, ch in enumerate(row)
            if ch != "." and (only is None or ch in only)]


def rects(pixels, pal):
    return "".join(
        f'<rect x="{x * CELL}" y="{y * CELL}" width="{CELL}" height="{CELL}" fill="{pal[c]}"/>'
        for x, y, c in pixels)


def flip(grid):
    return [r[::-1] for r in grid]


def stage_for(pet, streak):
    return max(i for i, s in enumerate(PETS[pet]["stages"]) if streak >= s[0])


def sprite(pet, stage):
    """Return (svg, shadow_rx)."""
    P = lambda extra=None: {**PALETTE, **(extra or {})}
    L = lambda grid, x, y, pal, cls=None, only=None: (
        (f'<g class="{cls}">' if cls else "<g>") + rects(px(grid, x, y, only), pal) + "</g>")
    if stage == 0:
        pal = P(PETS[pet]["egg"])
        return (f'<g transform="translate({(CW - 12) // 2 * CELL},{(GROUND - 14) * CELL})">'
                f'<g class="wobble">{rects(px(EGG), pal)}</g></g>'), 45

    parts, pal, rx = [], P(), 62
    if pet == "chicken":
        if stage == 1:
            base, rx = CHICK, 52
            parts.append(L(base, 0, 0, pal, only=set("KYyAPQ")))
            parts.append(L(base, 0, 0, pal, "eyes", only="E"))
        else:
            base = HEN
            if stage == 3: pal = P(PAL_ROOSTER)
            if stage == 4: pal = P(PAL_PHOENIX)
            if stage >= 3:
                parts.append(L(FAN, -3, 5, pal)); parts.append(L(flip(FAN), 18, 5, pal))
            if stage == 4:
                parts.insert(0, L(WING_S, -4, 4, pal, "wingL"))
                parts.insert(1, L(flip(WING_S), 17, 4, pal, "wingR"))
            parts.append(L(base, 0, 0, pal, only=set("KWgLRAQ")))
            if stage < 3:
                parts.append(L(base, 0, 0, pal, "eyes", only="E"))
            else:
                parts += [L(HEN_SHADES, 0, 5, pal), L(HEN_SCARF, 0, 12, pal)]
            if stage == 4:
                parts.append(L(FLAME, 0, -1, pal))
    H = len(base)
    return (f'<g transform="translate({OX * CELL},{(GROUND - H) * CELL})">'
            f'<g class="bob">{"".join(parts)}</g></g>'), rx


def sparkles(stage, color):
    if stage < 2:
        return ""
    spots = [(3, 19), (28, 18), (4, 25), (27, 24)][: stage]
    s = ""
    for i, (x, y) in enumerate(spots):
        def r(dx, dy, o):
            return (f'<rect x="{(x + dx) * CELL}" y="{(y + dy) * CELL}" width="{CELL}" '
                    f'height="{CELL}" fill="{color}" opacity="{o}"/>')
        s += (f'<g class="spark" style="animation-delay:{i * 0.4}s">'
              + r(0, 0, 1) + r(-1, 0, .5) + r(1, 0, .5) + r(0, -1, .5) + r(0, 1, .5) + '</g>')
    return s


def progress_bar(cfg, streak, stage, y, W):
    stages = cfg["stages"]
    lo, _, nxt = stages[stage]
    segs, width, x0 = 14, W - 60, 30
    if nxt is None:
        filled, label = segs, "MAX LEVEL REACHED"
    else:
        filled = int(segs * (streak - lo) / (nxt - lo))
        left = nxt - streak
        label = f"{left} DAY{'S' if left != 1 else ''} TO {stages[stage + 1][1]}"
    sw = width / segs
    bar = "".join(
        f'<rect x="{x0 + i * sw + 1:.1f}" y="{y}" width="{sw - 2:.1f}" height="10" '
        f'fill="{cfg["accent"] if i < filled else "#2c2433"}"/>' for i in range(segs))
    return bar + f'<text x="{W // 2}" y="{y + 26}" text-anchor="middle" class="sm">{label}</text>'


def css(cfg):
    return (
        "text{font-family:'Courier New',monospace;font-weight:bold;letter-spacing:1px}"
        f".t{{font-size:18px;fill:{cfg['title']}}}.sm{{font-size:11px;fill:{cfg['dim']}}}"
        f".m{{font-size:13px;fill:{cfg['accent']}}}"
        ".bob{animation:bob 1.2s steps(1,end) infinite}"
        "@keyframes bob{0%{transform:translateY(0)}50%{transform:translateY(-5px)}}"
        ".wobble{transform-box:fill-box;transform-origin:50% 100%;animation:wob 2s ease-in-out infinite}"
        "@keyframes wob{0%,55%,100%{transform:rotate(0)}65%{transform:rotate(-7deg)}80%{transform:rotate(7deg)}}"
        ".tail{transform-box:fill-box;transform-origin:0 100%;animation:wag 1.4s ease-in-out infinite}"
        "@keyframes wag{0%,100%{transform:rotate(-6deg)}50%{transform:rotate(10deg)}}"
        ".eyes{transform-box:fill-box;transform-origin:center;animation:blink 4s infinite}"
        "@keyframes blink{0%,92%,100%{transform:scaleY(1)}95%{transform:scaleY(.1)}}"
        ".wingL{transform-box:fill-box;transform-origin:100% 100%;animation:fl 1s ease-in-out infinite}"
        ".wingR{transform-box:fill-box;transform-origin:0 100%;animation:fr 1s ease-in-out infinite}"
        "@keyframes fl{0%,100%{transform:rotate(0)}50%{transform:rotate(-12deg)}}"
        "@keyframes fr{0%,100%{transform:rotate(0)}50%{transform:rotate(12deg)}}"
        ".spark{animation:tw 1.6s ease-in-out infinite}"
        "@keyframes tw{0%,100%{opacity:0}50%{opacity:1}}"
    )


def render(pet, streak):
    cfg = PETS[pet]
    stage = stage_for(pet, streak)
    name = cfg["stages"][stage][1]
    W, H = CW * CELL, CH * CELL + 100
    msg = "STREAK BROKE! COMMIT TO HATCH" if streak == 0 else f"{streak}-DAY STREAK"
    body, rx = sprite(pet, stage)
    return f'''<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}">
<style>{css(cfg)}</style>
<rect x="2" y="2" width="{W - 4}" height="{H - 4}" rx="10" fill="{cfg['bg']}" stroke="{cfg['accent']}" stroke-width="3"/>
<rect x="8" y="8" width="{W - 16}" height="{H - 16}" rx="6" fill="none" stroke="#2c2433" stroke-width="2" stroke-dasharray="4 4"/>
<text x="{W // 2}" y="28" text-anchor="middle" class="t">{name}</text>
{sparkles(stage, cfg['spark'])}
<ellipse cx="{W // 2}" cy="{GROUND * CELL + 2}" rx="{rx}" ry="7" fill="#000" opacity=".4"/>
{body}
<text x="{W // 2}" y="{CH * CELL + 22}" text-anchor="middle" class="m">DAY {streak}</text>
<text x="{W // 2}" y="{CH * CELL + 40}" text-anchor="middle" class="sm">{msg}</text>
{progress_bar(cfg, streak, stage, CH * CELL + 52, W)}
</svg>'''


# ------------------------------------------------------------------ streak
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




if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--streak", type=int)
    ap.add_argument("--all", action="store_true", help="write preview SVGs for every stage")
    ap.add_argument("--outdir", default="pet")
    a = ap.parse_args()
    if a.all:
        os.makedirs("pet/preview", exist_ok=True)
        for s in (0, 3, 12, 45, 150):
            open(f"pet/preview/chicken_{stage_for('chicken', s)}_day{s}.svg", "w").write(render("chicken", s))
    else:
        streak = a.streak if a.streak is not None else fetch_streak(os.environ["GH_USER"], os.environ["GH_TOKEN"])
        os.makedirs(a.outdir, exist_ok=True)
        open(os.path.join(a.outdir, "chicken.svg"), "w").write(render("chicken", streak))
        print(f"streak={streak} stage={PETS['chicken']['stages'][stage_for('chicken', streak)][1]}")