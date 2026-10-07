"""Render the engineering-activity panel for the profile README.

Reads public metadata for the featured repositories from the GitHub REST API
and writes a self-hosted SVG (assets/activity.svg) in the profile's
aurora-glass style. Standard library only. Every number shown comes from
the API; nothing is estimated.

Usage:
    python scripts/build_activity.py                    # live API (uses GITHUB_TOKEN if set)
    python scripts/build_activity.py --data snap.json   # offline snapshot
"""
from __future__ import annotations

import argparse
import json
import os
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from xml.sax.saxutils import escape

USER = "yaswanthakkireddy"
FEATURED = ["cortexagent", "MigrationLens", "NeuroShield", "fairlend", "ExperimentOS", "modelwatch", "carbonledgerx"]
ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "assets" / "activity.svg"

SANS = "Inter, 'Segoe UI', -apple-system, BlinkMacSystemFont, 'Helvetica Neue', Arial, sans-serif"
MONO = "'JetBrains Mono', ui-monospace, SFMono-Regular, Menlo, Consolas, 'Liberation Mono', monospace"
C = dict(base="#060A14", card="#0A1120", ink="#F1F6FF", soft="#B6C2D9", muted="#7F8BA6", dim="#4B587A",
         cyan="#22D3EE", sky="#38BDF8", blue="#3B82F6", violet="#8B5CF6", mint="#2DD4BF")
RAMP = [C["cyan"], C["blue"], C["violet"], C["mint"], "#64748B", "#334155"]


def _get(url: str):
    req = urllib.request.Request(url, headers={"Accept": "application/vnd.github+json", "User-Agent": USER})
    token = os.environ.get("GITHUB_TOKEN")
    if token:
        req.add_header("Authorization", f"Bearer {token}")
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.load(resp)


def fetch() -> list[dict]:
    out = []
    for name in FEATURED:
        r = _get(f"https://api.github.com/repos/{USER}/{name}")
        out.append({"name": r["name"], "pushed_at": r["pushed_at"], "langs": _get(r["languages_url"])})
    return out


def language_mix(repos: list[dict], top: int = 4) -> list[tuple[str, float]]:
    totals: dict[str, int] = {}
    for r in repos:
        for lang, size in r["langs"].items():
            totals[lang] = totals.get(lang, 0) + size
    grand = sum(totals.values()) or 1
    ranked = sorted(totals.items(), key=lambda kv: kv[1], reverse=True)
    mix = [(k, v / grand) for k, v in ranked[:top]]
    rest = sum(v for _, v in ranked[top:]) / grand
    if rest > 0.0005:
        mix.append(("Other", rest))
    return mix


def render(repos: list[dict], now: datetime) -> str:
    want = {n.lower() for n in FEATURED}
    repos = [r for r in repos if r["name"].lower() in want]
    rows = sorted(repos, key=lambda r: r["pushed_at"], reverse=True)
    W = 1200
    H = 150 + max(len(rows) * 40, 240) + 40
    p: list[str] = []

    p.append(f"""<defs>
<linearGradient id="fr" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="{C['sky']}" stop-opacity=".55"/>
<stop offset=".5" stop-color="{C['violet']}" stop-opacity=".25"/><stop offset="1" stop-color="{C['cyan']}" stop-opacity=".55"/></linearGradient>
<linearGradient id="gl" x1="0" y1="0" x2="1" y2="0"><stop offset="0" stop-color="{C['cyan']}" stop-opacity="0"/>
<stop offset=".5" stop-color="{C['cyan']}" stop-opacity=".9"/><stop offset="1" stop-color="{C['cyan']}" stop-opacity="0"/></linearGradient>
<filter id="bl" x="-50%" y="-50%" width="200%" height="200%"><feGaussianBlur stdDeviation="70"/></filter>
<clipPath id="cl"><rect x="1" y="1" width="{W - 2}" height="{H - 2}" rx="26"/></clipPath></defs>
<g clip-path="url(#cl)"><rect width="{W}" height="{H}" fill="{C['base']}"/><g filter="url(#bl)">
<circle cx="{W * .1:.0f}" cy="{H * .9:.0f}" r="230" fill="{C['violet']}" opacity=".38"/>
<circle cx="{W * .62:.0f}" cy="{H * .05:.0f}" r="220" fill="{C['cyan']}" opacity=".26"/>
<circle cx="{W * .98:.0f}" cy="{H * .85:.0f}" r="200" fill="{C['blue']}" opacity=".38"/></g></g>
<rect x="1" y="1" width="{W - 2}" height="{H - 2}" rx="26" fill="none" stroke="url(#fr)" stroke-width="1.5"/>
<rect x="18" y="18" width="{W - 36}" height="{H - 36}" rx="18" fill="{C['card']}" fill-opacity=".62" stroke="#FFFFFF" stroke-opacity=".08"/>
<rect x="{W * .2:.0f}" y="{H - 2}" width="{W * .6:.0f}" height="2" fill="url(#gl)"/>""")

    p.append(f'<text x="58" y="78" font-family="{MONO}" font-size="15" letter-spacing="2.6" fill="{C["cyan"]}">ENGINEERING ACTIVITY</text>')
    p.append(f'<text x="{W - 58}" y="78" text-anchor="end" font-family="{MONO}" font-size="14" fill="{C["dim"]}">'
             f'live from the GitHub API · {now:%d %b %Y}</text>')

    # language mix
    lx, lw = 58, 500
    p.append(f'<text x="{lx}" y="126" font-family="{SANS}" font-size="22" font-weight="700" fill="{C["ink"]}">Language mix</text>')
    p.append(f'<text x="{lx}" y="152" font-family="{SANS}" font-size="16" fill="{C["muted"]}">Share of code across {len(repos)} featured repositories</text>')
    mix = language_mix(repos)
    by, bh = 178, 14
    p.append(f'<clipPath id="bar"><rect x="{lx}" y="{by}" width="{lw}" height="{bh}" rx="7"/></clipPath>'
             f'<rect x="{lx}" y="{by}" width="{lw}" height="{bh}" rx="7" fill="#FFFFFF" fill-opacity=".06"/><g clip-path="url(#bar)">')
    cur = lx
    for i, (_, share) in enumerate(mix):
        p.append(f'<rect x="{cur:.2f}" y="{by}" width="{share * lw:.2f}" height="{bh}" fill="{RAMP[i % len(RAMP)]}"/>')
        cur += share * lw
    p.append("</g>")
    for i, (lang, share) in enumerate(mix):
        y = 236 + i * 40
        p.append(f'<circle cx="{lx + 7}" cy="{y - 6}" r="6" fill="{RAMP[i % len(RAMP)]}"/>'
                 f'<text x="{lx + 24}" y="{y}" font-family="{SANS}" font-size="18" fill="{C["ink"]}">{escape(lang)}</text>'
                 f'<text x="{lx + lw}" y="{y}" text-anchor="end" font-family="{MONO}" font-size="16" fill="{C["muted"]}">{share * 100:.1f}%</text>')

    p.append(f'<line x1="610" y1="104" x2="610" y2="{H - 50}" stroke="#FFFFFF" stroke-opacity=".08"/>')

    # featured repos, most recent push first
    rx = 650
    p.append(f'<text x="{rx}" y="126" font-family="{SANS}" font-size="22" font-weight="700" fill="{C["ink"]}">Featured repositories</text>')
    p.append(f'<text x="{rx}" y="152" font-family="{SANS}" font-size="16" fill="{C["muted"]}">Most recent push first</text>')
    for i, r in enumerate(rows):
        y = 196 + i * 40
        pushed = datetime.fromisoformat(r["pushed_at"].replace("Z", "+00:00"))
        days = max((now - pushed).days, 0)
        age = "today" if days == 0 else ("1d ago" if days == 1 else f"{days}d ago")
        fresh = days <= 30
        p.append(f'<circle cx="{rx + 6}" cy="{y - 6}" r="4.5" fill="{C["mint"] if fresh else C["dim"]}"/>'
                 f'<text x="{rx + 22}" y="{y}" font-family="{MONO}" font-size="17" fill="{C["ink"]}">{escape(r["name"])}</text>'
                 f'<text x="{W - 58}" y="{y}" text-anchor="end" font-family="{MONO}" font-size="16" fill="{C["muted"]}">'
                 f'{pushed:%b %d, %Y} · {age}</text>')
        if i < len(rows) - 1:
            p.append(f'<line x1="{rx}" y1="{y + 15}" x2="{W - 58}" y2="{y + 15}" stroke="#FFFFFF" stroke-opacity=".06"/>')

    return (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" width="{W}" height="{H}" role="img" aria-labelledby="t d">'
            f'<title id="t">Engineering activity</title><desc id="d">Language mix across the featured repositories and the latest '
            f'push date of each, generated from the GitHub API.</desc>{"".join(p)}</svg>\n')


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", type=Path, help="offline JSON snapshot instead of the live API")
    ap.add_argument("--now", help="override the timestamp (ISO date) for reproducible snapshots")
    args = ap.parse_args()
    repos = json.loads(args.data.read_text()) if args.data else fetch()
    now = datetime.fromisoformat(args.now).replace(tzinfo=timezone.utc) if args.now else datetime.now(timezone.utc)
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(render(repos, now), encoding="utf-8")
    print("wrote", OUT.relative_to(ROOT))


if __name__ == "__main__":
    main()
