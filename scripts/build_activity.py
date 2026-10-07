"""Build the profile's Engineering Telemetry panel using only the standard library.

The seven selected public projects are the entire scope. The profile repository is
excluded so its own refresh commits cannot create an activity feedback loop.
Recorded evidence is deliberately separate from the current main-branch CI
snapshot. A successful workflow is not a claim that every collected test passed.

No clock, relative age, run timestamp, or run ID enters the SVG. Re-fetching the
same HEADs, source commit dates, and CI outcomes produces exactly the same bytes,
even after a rerun. Absolute last-main-commit dates come from GitHub, not the clock.
API/validation failures occur before writing; the last good asset is preserved.

Usage:
    python scripts/build_activity.py
    python scripts/build_activity.py --data snapshot.json --output preview.svg

Offline data: a list of {"repo": ..., "head": ..., "committed_at": ISO timestamp,
"workflow": null or workflow
object, "run": null or latest main-branch workflow-run object}. CI scope is each
repository's ci.yml, plus CortexAgent's ragas_gate.yml; absent/disabled workflows
are explicit.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import re
import tempfile
from urllib.parse import quote, urlencode
from urllib.request import Request, urlopen
from xml.sax.saxutils import escape

USER = "yaswanthakkireddy"
ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "assets" / "activity.svg"
CI_PATH = ".github/workflows/ci.yml"
CI_PATHS = {"cortexagent": ".github/workflows/ragas_gate.yml"}
PROJECTS = (
    ("cortexagent", "CortexAgent", "Flagship",
     ("20/20 single-LLM baseline", "Single-model behavioral contract")),
    ("MigrationLens", "MigrationLens", "Flagship",
     ("138 passed / 3 skipped (documented)", "37/37 expected Sakila fixture findings")),
    ("NeuroShield", "NeuroShield", "Flagship",
     ("GraphSAGE PR-AUC 0.5177", "Elliptic temporal holdout (40–49)")),
    ("fairlend", "FairLend", "Flagship",
     ("15 passed / 19 skipped", "Recorded CI result: 2026-10-06")),
    ("ExperimentOS", "ExperimentOS", "Supporting",
     ("30 passed", "Recorded CI result: 2026-10-06")),
    ("modelwatch", "ModelWatch", "Supporting",
     ("43 checks (documented)", "Artifact-dependent skips")),
    ("TOSCO", "TOSCO", "Flagship",
     ("SHA256 proof chain + HMAC token", "Seeded evidence / mock-bank prototype")),
)
SANS = "Inter, 'Segoe UI', Arial, sans-serif"
MONO = "ui-monospace, SFMono-Regular, Menlo, Consolas, monospace"
COLORS = {
    "ink": "#F1F6FF", "soft": "#B6C2D9", "muted": "#8995AD",
    "cyan": "#00C8FF", "good": "#A3FF39", "warn": "#FBBF24",
    "bad": "#FB7185",
}


def _get(url: str) -> dict:
    # All source repositories are public. Anonymous read access avoids requiring
    # a personal token or granting cross-repository privileges to this workflow.
    req = Request(url, headers={
        "Accept": "application/vnd.github+json",
        "User-Agent": USER + "-profile-telemetry",
        "X-GitHub-Api-Version": "2022-11-28",
    })
    with urlopen(req, timeout=30) as response:
        data = json.load(response)
    if not isinstance(data, dict):
        raise ValueError("Expected a GitHub API object")
    return data


def fetch() -> list[dict]:
    result = []
    for repo, *_ in PROJECTS:
        base = f"https://api.github.com/repos/{USER}/{quote(repo)}"
        branch = _get(base + "/branches/main")
        head = branch["commit"]["sha"]
        committed_at = branch["commit"]["commit"]["committer"]["date"]
        listing = _get(base + "/actions/workflows?per_page=100")
        workflows = listing["workflows"]
        if listing["total_count"] > len(workflows):
            raise ValueError(f"{repo}: workflow inventory is incomplete")
        tracked_path = CI_PATHS.get(repo, CI_PATH)
        workflow = next((w for w in workflows if w["path"] == tracked_path), None)
        run = None
        if workflow is not None and workflow["state"] == "active":
            query = urlencode({"branch": "main", "per_page": 1})
            runs = _get(base + f"/actions/workflows/{workflow['id']}/runs?{query}")
            if runs["total_count"] and not runs["workflow_runs"]:
                raise ValueError(f"{repo}: run inventory is incomplete")
            run = next(iter(runs["workflow_runs"]), None)
        result.append({"repo": repo, "head": head, "committed_at": committed_at,
                       "workflow": workflow, "run": run})
    return result


def ci_status(row: dict) -> tuple[str, str]:
    """Never promote an older successful run to a claim about current main."""
    workflow = row["workflow"]
    if workflow is None:
        return "No tracked CI workflow", "muted"
    if workflow["state"] != "active":
        return "CI disabled", "warn"
    run = row["run"]
    if run is None or run["head_sha"] != row["head"] or run["head_branch"] != "main":
        return "No run for this HEAD", "warn"
    if run["status"] != "completed":
        return "Pending on main", "warn"
    conclusion = run["conclusion"]
    if conclusion == "success":
        return "Passing on main", "good"
    if conclusion in {"failure", "timed_out", "startup_failure", "action_required"}:
        return "Needs attention", "bad"
    if conclusion == "cancelled":
        return "Cancelled on main", "warn"
    if conclusion == "skipped":
        return "Skipped on main", "muted"
    if conclusion == "neutral":
        return "Neutral on main", "muted"
    return "Result unavailable", "warn"


def commit_date(row: dict) -> str:
    """Normalize the source commit timestamp to an absolute UTC calendar date."""
    timestamp = datetime.fromisoformat(row["committed_at"].replace("Z", "+00:00"))
    if timestamp.tzinfo is None:
        raise ValueError("Commit timestamp must include a timezone")
    return timestamp.astimezone(timezone.utc).date().isoformat()


def validate(rows: list[dict]) -> dict[str, dict]:
    expected = {p[0] for p in PROJECTS}
    mapped = {r["repo"]: r for r in rows}
    if len(mapped) != len(rows) or set(mapped) != expected:
        raise ValueError("Snapshot must contain each selected project exactly once")
    for row in rows:
        if not re.fullmatch(r"[0-9a-f]{40}", row["head"]):
            raise ValueError("Invalid main HEAD SHA")
        commit_date(row)
        workflow = row["workflow"]
        if workflow is not None and workflow["path"] != CI_PATHS.get(row["repo"], CI_PATH):
            raise ValueError("Unexpected CI workflow")
        ci_status(row)  # Validate required status fields before any output.
    return mapped


def _text(x: int, y: int, value: str, *, size: int = 18,
          color: str = "soft", weight: int = 400, mono: bool = False) -> str:
    family = MONO if mono else SANS
    return (f'<text x="{x}" y="{y}" font-family="{family}" font-size="{size}" '
            f'font-weight="{weight}" fill="{COLORS[color]}">{escape(value)}</text>')


def render(rows: list[dict]) -> str:
    mapped = validate(rows)
    width, height = 1200, 264 + len(PROJECTS) * 72
    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" '
        f'viewBox="0 0 {width} {height}" role="img" aria-labelledby="title desc">',
        '<title id="title">Engineering Telemetry</title>',
        '<desc id="desc">Scoped evidence for five flagship and two supporting '
        'projects, with CI status checked against each main branch HEAD and '
        'absolute last-main-commit dates in UTC. '
        'Recorded test counts are not live test results.</desc>',
        '<defs><linearGradient id="edge" x1="0" y1="0" x2="1" y2="1">'
        '<stop stop-color="#00C8FF" stop-opacity=".65"/>'
        '<stop offset="1" stop-color="#3B82F6" stop-opacity=".22"/>'
        '</linearGradient></defs>',
        f'<rect x="1" y="1" width="1198" height="{height - 2}" rx="24" '
        'fill="#05070E" stroke="url(#edge)"/>',
        f'<rect x="18" y="18" width="1164" height="{height - 36}" rx="16" fill="#090D16"/>',
        _text(48, 62, "ENGINEERING TELEMETRY", size=16, color="cyan", weight=600, mono=True),
        _text(48, 97, "Evidence and recent engineering", size=27, color="ink", weight=700),
        _text(48, 126, "Scoped results, main-branch CI, and last main commit dates (UTC).", size=17),
        _text(48, 169, "PROJECT / LAST COMMIT", size=13, color="muted", weight=600, mono=True),
        _text(278, 169, "RECORDED EVIDENCE", size=13, color="muted", weight=600, mono=True),
        _text(865, 169, "CI AT MAIN HEAD", size=13, color="muted", weight=600, mono=True),
    ]
    for i, (repo, label, tier, evidence) in enumerate(PROJECTS):
        row = mapped[repo]
        top = 190 + i * 72
        status, tone = ci_status(row)
        parts.extend((
            f'<line x1="48" y1="{top}" x2="1152" y2="{top}" stroke="#FFFFFF" stroke-opacity=".07"/>',
            _text(48, top + 29, label, size=20, color="ink", weight=600),
            _text(48, top + 53, tier + " · " + commit_date(row), size=14, color="muted"),
            _text(278, top + 29, evidence[0], size=18, color="ink"),
            _text(278, top + 53, evidence[1], size=16, color="muted"),
            f'<circle cx="870" cy="{top + 24}" r="4" fill="{COLORS[tone]}"/>',
            _text(884, top + 29, status, size=16, color=tone),
            _text(884, top + 53, "main @ " + row["head"][:7], size=14, color="muted", mono=True),
        ))
    parts.extend((
        f'<line x1="48" y1="{height - 74}" x2="1152" y2="{height - 74}" stroke="#FFFFFF" stroke-opacity=".07"/>',
        _text(48, height - 46, "Daily snapshot · CI runs matched to main commits · sources linked below.", size=16),
        '</svg>\n',
    ))
    svg = "".join(parts)
    width = 600 if 'width="600"' in svg[:180] else 1200
    y = 134 if width == 600 else 138
    motion = (f'<g aria-hidden="true"><rect x="32" y="{y}" width="60" height="2" '
              f'fill="#00c8ff"><animate attributeName="x" values="32;{width - 92};32" '
              'dur="10s" repeatCount="indefinite"/></rect></g>')
    if width == 600:
        motion += '<g aria-hidden="true">'
        for i in range(len(PROJECTS)):
            motion += (f'<circle cx="18" cy="{142 + i * 196 + 94}" r="3" fill="#00c8ff">'
                       f'<animate attributeName="opacity" values=".2;.9;.2" dur="4s" begin="{i % 3}s" '
                       'repeatCount="indefinite"/></circle>')
        motion += '</g>'
    return svg.replace("</svg>", motion + "</svg>")


def render_mobile(rows: list[dict]) -> str:
    """A stacked companion preserves readable type on narrow profile screens."""
    mapped = validate(rows)
    height = 204 + len(PROJECTS) * 196
    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="600" height="{height}" '
        f'viewBox="0 0 600 {height}" role="img" aria-labelledby="title desc">',
        '<title id="title">Engineering Telemetry</title>',
        '<desc id="desc">Mobile layout of the same scoped project evidence, '
        'main-commit dates in UTC, and main-HEAD CI snapshot.</desc>',
        f'<rect x="1" y="1" width="598" height="{height - 2}" rx="24" fill="#05070E" '
        'stroke="#00C8FF" stroke-opacity=".4"/>',
        _text(32, 60, "ENGINEERING TELEMETRY", size=24, color="cyan", weight=600),
        _text(32, 98, "Evidence + latest main CI", size=26, color="ink", weight=700),
        _text(32, 126, "Recorded project scope", size=20, color="muted"),
    ]
    for i, (repo, label, tier, evidence) in enumerate(PROJECTS):
        row = mapped[repo]
        top = 142 + i * 196
        status, tone = ci_status(row)
        parts.extend((
            f'<line x1="32" y1="{top}" x2="568" y2="{top}" stroke="#FFFFFF" stroke-opacity=".1"/>',
            _text(32, top + 40, label, size=31, color="ink", weight=600),
            _text(32, top + 78, evidence[0], size=24, color="ink"),
            _text(32, top + 112, evidence[1], size=22, color="muted"),
            f'<circle cx="38" cy="{top + 142}" r="4" fill="{COLORS[tone]}"/>',
            _text(52, top + 149, status, size=22, color=tone),
            _text(32, top + 180, tier + " · " + commit_date(row) + " UTC · " +
                  row["head"][:7], size=19, color="muted"),
        ))
    parts.extend((
        _text(32, height - 30, "UTC dates · linked evidence below", size=20, color="muted"),
        '</svg>\n',
    ))
    return "".join(parts)


def write_if_changed(output: Path, content: str) -> bool:
    payload = content.encode("utf-8")
    if output.exists() and output.read_bytes() == payload:
        return False
    output.parent.mkdir(parents=True, exist_ok=True)
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(dir=output.parent, delete=False) as handle:
            temporary = Path(handle.name)
            handle.write(payload)
        os.replace(temporary, output)
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)
    return True


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data", type=Path, help="offline JSON snapshot")
    parser.add_argument("--output", type=Path, default=OUT)
    args = parser.parse_args(argv)
    rows = json.loads(args.data.read_text(encoding="utf-8")) if args.data else fetch()
    content = render(rows)
    mobile = render_mobile(rows) if args.output == OUT else None
    changed = write_if_changed(args.output, content)
    if mobile is not None:
        changed = write_if_changed(OUT.with_name("activity-mobile.svg"), mobile) or changed
    print("Updated Engineering Telemetry" if changed else "Engineering Telemetry is unchanged")


if __name__ == "__main__":
    main()
