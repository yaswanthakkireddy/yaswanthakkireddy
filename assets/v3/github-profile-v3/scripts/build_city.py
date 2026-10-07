"""Render the 3D contribution city (assets/city.svg) from public GitHub contributions.

Each tower is one day with public contributions; its height follows GitHub's
own intensity level (1-4). Days without contributions stay flat street tiles.
Standard library only.

Usage:
    python scripts/build_city.py                         # GitHub GraphQL (needs GITHUB_TOKEN)
    python scripts/build_city.py --data assets/contribution-source.json
"""
from __future__ import annotations

import argparse
import json
import math
import os
import random
import urllib.request
from datetime import date, timedelta
from pathlib import Path

USER = "yaswanthakkireddy"
ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "assets" / "v3" / "city.svg"
LEVELS = {"NONE": 0, "FIRST_QUARTILE": 1, "SECOND_QUARTILE": 2, "THIRD_QUARTILE": 3, "FOURTH_QUARTILE": 4}

C = dict(base="#060A16", ink="#F8FAFC", soft="#C7D2E4", muted="#8592AD", dim="#4D5A78",
         blue="#3B82F6", sky="#38BDF8", mint="#2EE6B6", red="#FF4D5E", amber="#FFC857")
SANS = "Inter, 'Segoe UI', -apple-system, BlinkMacSystemFont, 'Helvetica Neue', Arial, sans-serif"
MONO = "'JetBrains Mono', ui-monospace, SFMono-Regular, Menlo, Consolas, monospace"


def fetch(year: int) -> dict[str, int]:
    q = """query($u:String!,$f:DateTime!,$t:DateTime!){user(login:$u){contributionsCollection(from:$f,to:$t){
           contributionCalendar{weeks{contributionDays{date contributionLevel}}}}}}"""
    body = json.dumps({"query": q, "variables": {"u": USER, "f": f"{year}-01-01T00:00:00Z", "t": f"{year}-12-31T23:59:59Z"}})
    req = urllib.request.Request("https://api.github.com/graphql", data=body.encode(),
                                 headers={"Authorization": f"Bearer {os.environ['GITHUB_TOKEN']}", "User-Agent": USER})
    with urllib.request.urlopen(req, timeout=30) as r:
        data = json.load(r)
    weeks = data["data"]["user"]["contributionsCollection"]["contributionCalendar"]["weeks"]
    return {d["date"]: LEVELS.get(d["contributionLevel"], 0) for w in weeks for d in w["contributionDays"]}


def render(levels: dict[str, int], year: int) -> str:
    random.seed(year)
    W, H = 1200, 460
    tw, th = 15.0, 7.5            # isometric tile half-sizes
    ox, oy = 168, 150             # origin of the grid (week 0, Sunday)
    start = date(year, 1, 1)
    first_sunday = start - timedelta(days=(start.weekday() + 1) % 7)
    p = []

    # sky
    p.append(f'''<defs>
<linearGradient id="sky" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#050816"/><stop offset=".65" stop-color="#0B1430"/><stop offset="1" stop-color="#111C3D"/></linearGradient>
<linearGradient id="fr" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="{C['blue']}"/><stop offset=".5" stop-color="{C['mint']}"/><stop offset="1" stop-color="{C['red']}"/></linearGradient>
<radialGradient id="moon" cx=".4" cy=".4" r=".6"><stop offset="0" stop-color="#FFFFFF"/><stop offset="1" stop-color="#C7D2E4"/></radialGradient>
<filter id="glow" x="-50%" y="-50%" width="200%" height="200%"><feGaussianBlur stdDeviation="3"/></filter>
<clipPath id="cl"><rect x="1" y="1" width="{W - 2}" height="{H - 2}" rx="24"/></clipPath></defs>
<g clip-path="url(#cl)"><rect width="{W}" height="{H}" fill="url(#sky)"/>''')
    for _ in range(70):
        x, y, r = random.uniform(10, W - 10), random.uniform(10, H * 0.45), random.uniform(.5, 1.5)
        tw_anim = f'<animate attributeName="opacity" values=".2;1;.2" dur="{random.uniform(2, 6):.1f}s" begin="{random.uniform(0, 5):.1f}s" repeatCount="indefinite"/>' if random.random() < .3 else ""
        p.append(f'<circle cx="{x:.0f}" cy="{y:.0f}" r="{r:.1f}" fill="#FFFFFF" opacity=".55">{tw_anim}</circle>')
    p.append(f'<circle cx="1080" cy="78" r="26" fill="url(#moon)" opacity=".9"/><circle cx="1092" cy="70" r="24" fill="#0B1430" opacity=".85"/>')

    # simple isometric: x grows with week, y grows with weekday
    def P(col: float, row: float) -> tuple[float, float]:
        return ox + col * tw * 1.0 + row * tw * 0.9, oy + row * th * 1.6 - col * th * 0.18 + 120

    cells = []
    for wk in range(53):
        for dow in range(7):
            d = first_sunday + timedelta(days=wk * 7 + dow)
            if d.year != year:
                continue
            cells.append((wk, dow, d, levels.get(d.isoformat(), 0)))
    heights = {0: 0, 1: 22, 2: 46, 3: 72, 4: 104}
    for wk, dow, d, lv in sorted(cells, key=lambda c: (c[1], c[0])):
        x, y = P(wk, dow)
        a, b = tw * 0.92, th * 0.92
        top = [(x, y - b), (x + a, y), (x, y + b), (x - a, y)]
        if lv == 0:
            pts = " ".join(f"{px:.1f},{py:.1f}" for px, py in top)
            p.append(f'<polygon points="{pts}" fill="#14204A" stroke="#1E2C5C" stroke-width=".6"/>')
            continue
        h = heights[lv]
        col = {1: C["blue"], 2: C["sky"], 3: C["mint"], 4: C["mint"]}[lv]
        left = [(x - a, y), (x, y + b), (x, y + b - h), (x - a, y - h)]
        right = [(x, y + b), (x + a, y), (x + a, y - h), (x, y + b - h)]
        roof = [(px, py - h) for px, py in top]
        f = lambda pts: " ".join(f"{px:.1f},{py:.1f}" for px, py in pts)
        p.append(f'<polygon points="{f(left)}" fill="{col}" opacity=".55"/>'
                 f'<polygon points="{f(right)}" fill="{col}" opacity=".8"/>'
                 f'<polygon points="{f(roof)}" fill="{col}"/>')
        # windows
        for k in range(1, int(h / 11)):
            wy = y - k * 11 + b * 0.3
            if random.random() < .75:
                p.append(f'<rect x="{x + a * 0.35:.1f}" y="{wy:.1f}" width="2.6" height="3.2" fill="#FFF7D6" opacity=".85"/>')
            if random.random() < .6:
                p.append(f'<rect x="{x - a * 0.6:.1f}" y="{wy - 1:.1f}" width="2.6" height="3.2" fill="#FFF7D6" opacity=".6"/>')
        if lv == 4:  # beacon on the tallest towers
            p.append(f'<circle cx="{x:.1f}" cy="{y - h - b - 4:.1f}" r="2.6" fill="{C["red"]}">'
                     f'<animate attributeName="opacity" values="1;.15;1" dur="1.6s" repeatCount="indefinite"/></circle>'
                     f'<circle cx="{x:.1f}" cy="{y - h - b - 4:.1f}" r="6" fill="{C["red"]}" opacity=".35" filter="url(#glow)"/>')
    p.append("</g>")

    active = sum(1 for v in levels.values() if v > 0 and v is not None)
    months = ["JAN", "FEB", "MAR", "APR", "MAY", "JUN", "JUL", "AUG", "SEP", "OCT", "NOV", "DEC"]
    for m in range(12):
        d = date(year, m + 1, 1)
        wk = (d - first_sunday).days // 7
        x, _ = P(wk, 3.0)
        _, y = P(wk, 7.6)
        p.append(f'<text x="{x:.0f}" y="{y + 18:.0f}" font-family="{MONO}" font-size="12" letter-spacing="1.5" fill="{C["dim"]}">{months[m]}</text>')

    p.append(f'<text x="48" y="58" font-family="{MONO}" font-size="15" letter-spacing="2.6" fill="{C["mint"]}">// CONTRIBUTION CITY · {year}</text>'
             f'<text x="48" y="92" font-family="{SANS}" font-size="28" font-weight="800" fill="{C["ink"]}">Every tower is a day I shipped in public</text>'
             f'<text x="48" y="118" font-family="{SANS}" font-size="15" fill="{C["muted"]}">{active} active days · height follows GitHub\'s contribution level · rebuilt daily</text>')
    p.append(f'<rect x="1" y="1" width="{W - 2}" height="{H - 2}" rx="24" fill="none" stroke="url(#fr)" stroke-width="1.6"/>')
    return (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" width="{W}" height="{H}" role="img" aria-labelledby="t d">'
            f'<title id="t">Contribution city {year}</title><desc id="d">Isometric night skyline where each tower is a day with public GitHub '
            f'contributions in {year}; {active} active days.</desc>{"".join(p)}</svg>\n')


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", type=Path)
    ap.add_argument("--year", type=int, default=date.today().year)
    a = ap.parse_args()
    if a.data:
        raw = json.loads(a.data.read_text())
        levels = {d["date"]: int(d["level"]) for d in raw["days"]}
        year = raw.get("year", a.year)
    else:
        year = a.year
        levels = fetch(year)
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(render(levels, year), encoding="utf-8")
    print("wrote", OUT.relative_to(ROOT))


if __name__ == "__main__":
    main()
