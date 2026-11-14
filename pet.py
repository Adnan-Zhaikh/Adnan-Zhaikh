import os, datetime as dt, requests

USER = os.environ["GH_USER"]
TOKEN = os.environ["GH_TOKEN"]

def streak():
    """Count consecutive days with contributions, ending today or yesterday."""
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
    days = [d for w in weeks for d in w["contributionDays"]]
    days.sort(key=lambda d: d["date"], reverse=True)

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
    (0,   "Egg",       "#9aa5b1", "🥚"),
    (1,   "Hatchling", "#7fd1ae", "🐣"),
    (7,   "Sprout",    "#4caf50", "🌱"),
    (30,  "Grown",     "#2196f3", "😎"),
    (100, "Champion",  "#ffb300", "👑"),
    (365, "Legend",    "#e91e63", "🔥"),
]

def render(n):
    stage = max((s for s in STAGES if n >= s[0]), key=lambda s: s[0])
    _, name, color, emoji = stage
    nxt = next((s for s in STAGES if s[0] > n), None)
    bar = 0 if not nxt else int(100 * (n - stage[0]) / (nxt[0] - stage[0]))

    return f'''<svg xmlns="http://www.w3.org/2000/svg" width="420" height="150" viewBox="0 0 420 150">
  <rect width="420" height="150" rx="14" fill="#0d1117"/>
  <text x="24" y="46" font-family="monospace" font-size="34">{emoji}</text>
  <text x="76" y="40" fill="{color}" font-family="monospace" font-size="20">{name}</text>
  <text x="76" y="64" fill="#8b949e" font-family="monospace" font-size="13">{n} day streak</text>
  <rect x="76" y="78" width="300" height="10" rx="5" fill="#21262d"/>
  <rect x="76" y="78" width="{3*bar}" height="10" rx="5" fill="{color}"/>
  <text x="76" y="112" fill="#8b949e" font-family="monospace" font-size="12">
    {"max level" if not nxt else f"next: {nxt[1]} at {nxt[0]} days"}</text>
</svg>'''

n = streak()
open("pet.svg", "w").write(render(n))
print(f"streak {n}")
