import os, datetime as dt, requests

USER = os.environ["GH_USER"]
TOKEN = os.environ["GH_TOKEN"]

def streak():
    """Consecutive days with contributions, ending today or yesterday."""
    q = """
    query($u:String!){ user(login:$u){ contributionsCollection{
      contributionCalendar{ weeks{ contributionDays{ date contributionCount } } } } } }
    """
    r = requests.post("https://api.github.com/graphql",
                      json={"query": q, "variables": {"u": USER}},
                      headers={"Authorization": f"bearer {TOKEN}"})
    r.raise_for_status()
    weeks = r.json()["data"]["user"]["contributionsCollection"] \
                     ["contributionCalendar"]["weeks"]
    days = sorted((d for w in weeks for d in w["contributionDays"]),
                  key=lambda d: d["date"], reverse=True)

    today = dt.date.today()
    n = 0
    for d in days:
        day = dt.date.fromisoformat(d["date"])
        if day > today:
            continue
        if d["contributionCount"] > 0:
            n += 1
        elif (today - day).days <= 1 and n == 0:
            continue          # today not committed yet — grace period
        else:
            break
    return n

STAGES = [
    (0,   "Egg",       "#8b949e", "#30363d"),
    (1,   "Hatchling", "#7ee787", "#1f6f43"),
    (7,   "Wyrmling",  "#56d364", "#238636"),
    (30,  "Drake",     "#3fb950", "#2ea043"),
    (100, "Elder",     "#d29922", "#9e6a03"),
    (365, "Ancient",   "#f778ba", "#db61a2"),
]

def dragon(stage, scale, body, accent):
    """Draw the dragon for a given stage index (0-5)."""
    head = f'''
    <g>
      <path d="M150 70 q18 -16 34 -4 q10 8 6 20 q-4 12 -20 14 q-16 2 -22 -10 q-6 -12 2 -20 z"
            fill="{body}" stroke="{accent}" stroke-width="2"/>
      <circle cx="172" cy="76" r="3.5" fill="{"#f0f6fc" if stage < 4 else accent}"/>
      <circle cx="172" cy="76" r="1.6" fill="#0d1117"/>
    </g>'''
    # horns grow with stage
    horns = ""
    if stage >= 2:
        horns += f'<path d="M156 62 l-6 -14 l12 6 z" fill="{accent}"/>'
    if stage >= 3:
        horns += f'<path d="M166 58 l0 -16 l10 10 z" fill="{accent}"/>'
    if stage >= 4:
        horns += f'<path d="M148 68 l-14 -8 l4 12 z" fill="{accent}"/>'
    if stage >= 5:
        horns += f'<path d="M176 60 l10 -14 l2 14 z" fill="{accent}"/>'

    wings = ""
    if stage >= 2:
        s = 0.6 if stage == 2 else 1.0
        wings = f'''<path d="M132 92 q-{int(46*s)} -{int(30*s)} -{int(58*s)} -{int(6*s)}
                    q{int(18*s)} {int(18*s)} {int(10*s)} {int(34*s)} z"
                    fill="{accent}" opacity="0.55"/>'''
    if stage >= 3:
        wings += f'''<path d="M132 96 q-40 -6 -56 14 q22 4 30 16 z"
                     fill="{accent}" opacity="0.35"/>'''

    spark = ""
    if stage >= 3:
        spark = f'<circle cx="196" cy="82" r="{3 if stage == 3 else 5}" fill="{accent}" opacity="0.8"/>'
    if stage >= 5:
        spark += f'<circle cx="204" cy="86" r="3" fill="#ffd33d" opacity="0.9"/>'

    aura = ""
    if stage >= 5:
        aura = f'<circle cx="150" cy="86" r="52" fill="none" stroke="{accent}" stroke-width="2" opacity="0.35" stroke-dasharray="4 6"/>'

    if stage == 0:   # egg
        return f'''<g>
          <ellipse cx="150" cy="86" rx="26" ry="34" fill="{body}" stroke="{accent}" stroke-width="2"/>
          <path d="M136 70 l8 10 l-10 6 l9 8" fill="none" stroke="{accent}" stroke-width="1.5" opacity="0.8"/>
        </g>'''

    return f'''<g transform="translate(0,{0 if stage > 1 else 4})">
      {aura}{wings}
      <ellipse cx="150" cy="86" rx="{34 if stage > 1 else 26}" ry="{22 if stage > 1 else 18}"
               fill="{body}" stroke="{accent}" stroke-width="2"/>
      <path d="M118 92 q-14 6 -18 18 q14 -4 22 -10 z" fill="{body}" stroke="{accent}" stroke-width="2"/>
      {head}{horns}{spark}
    </g>'''

def render(n):
    idx = max(i for i, s in enumerate(STAGES) if n >= s[0])
    name, color, accent = STAGES[idx][1], STAGES[idx][2], STAGES[idx][3]
    nxt = STAGES[idx + 1] if idx + 1 < len(STAGES) else None
    bar = 0 if not nxt else int(100 * (n - STAGES[idx][0]) / (nxt[0] - STAGES[idx][0]))

    return f'''<svg xmlns="http://www.w3.org/2000/svg" width="420" height="170" viewBox="0 0 420 170">
  <rect width="420" height="170" rx="14" fill="#0d1117"/>
  <rect x="1" y="1" width="418" height="168" rx="13" fill="none" stroke="#30363d"/>
  {dragon(idx, 1, color, accent)}
  <text x="230" y="52" fill="{color}" font-family="monospace" font-size="20">{name}</text>
  <text x="230" y="76" fill="#8b949e" font-family="monospace" font-size="13">{n} day streak</text>
  <rect x="230" y="92" width="160" height="10" rx="5" fill="#21262d"/>
  <rect x="230" y="92" width="{1.6*bar:.0f}" height="10" rx="5" fill="{color}"/>
  <text x="230" y="126" fill="#8b949e" font-family="monospace" font-size="12">{
    "max level reached" if not nxt else f"next: {nxt[1]} at {nxt[0]} days"}</text>
</svg>'''

n = streak()
open("pet.svg", "w").write(render(n))
print(f"streak {n}")
