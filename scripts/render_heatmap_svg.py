#!/usr/bin/env python3
"""Render an animated 53-week GitHub-style contribution heatmap SVG."""
from __future__ import annotations

import html
import json
from datetime import date, timedelta
from pathlib import Path

INPUT = Path("data/contributions.json")
OUTPUT = Path("assets/contrib-heatmap.svg")
PALETTE = ["#161b22", "#0e4429", "#006d32", "#26a641", "#39d353"]

def sunday_index(d: date) -> int:
    return (d.weekday() + 1) % 7

def main() -> None:
    payload = json.loads(INPUT.read_text(encoding="utf-8"))
    days = payload.get("days", [])
    by_date = {date.fromisoformat(d["date"]): d for d in days}

    width, height = 860, 190
    left, top = 52, 45
    size, gap, weeks = 11, 3, 53
    pitch = size + gap

    last = max(by_date) if by_date else date.today()
    week_end = last + timedelta(days=(6 - sunday_index(last)))
    start = week_end - timedelta(days=(weeks * 7 - 1))

    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}" role="img" aria-labelledby="title desc">',
        '<title id="title">Ridham Pansara GitHub contribution heatmap</title>',
        '<desc id="desc">Animated 53-week contribution calendar generated from public GitHub profile data.</desc>',
        '<rect width="100%" height="100%" rx="14" fill="#0d1117" stroke="#30363d"/>',
        '<text x="24" y="27" fill="#58a6ff" font-family="ui-monospace,SFMono-Regular,Menlo,Monaco,Consolas,monospace" font-size="12">LIVE CONTRIBUTION ACTIVITY</text>',
    ]

    for label, row in [("Mon", 1), ("Wed", 3), ("Fri", 5)]:
        y = top + row * pitch + 9
        parts.append(f'<text x="18" y="{y}" fill="#8b949e" font-family="ui-monospace,SFMono-Regular,Menlo,Monaco,Consolas,monospace" font-size="9">{label}</text>')

    seen = set()
    for week in range(weeks):
        d = start + timedelta(days=week * 7)
        if d.day <= 7 and (d.year, d.month) not in seen:
            seen.add((d.year, d.month))
            x = left + week * pitch
            parts.append(f'<text x="{x}" y="40" fill="#8b949e" font-family="ui-monospace,SFMono-Regular,Menlo,Monaco,Consolas,monospace" font-size="9">{d.strftime("%b")}</text>')

    for week in range(weeks):
        for row in range(7):
            d = start + timedelta(days=week * 7 + row)
            info = by_date.get(d, {"count": 0, "level": 0})
            level = max(0, min(4, int(info.get("level", 0))))
            count = int(info.get("count", 0))
            x, y = left + week * pitch, top + row * pitch
            delay = min(1.7, 0.0028 * (week + row * 2) + 0.02)
            parts.append(
                f'<rect x="{x}" y="{y}" width="{size}" height="{size}" rx="2" fill="{PALETTE[level]}" opacity="0">'
                f'<title>{html.escape(d.isoformat())}: {count} contributions</title>'
                f'<animate attributeName="opacity" from="0" to="1" dur="0.22s" begin="{delay:.3f}s" fill="freeze"/>'
                '</rect>'
            )

    stats = payload.get("stats", {})
    total = stats.get("total", 0)
    current = stats.get("current_streak", 0)
    longest = stats.get("longest_streak", 0)
    footer = (
        f"{total:,} contributions · current streak {current}d · longest streak {longest}d"
        if days else
        "Contribution data refresh pending — GitHub Actions will populate this graph"
    )
    parts.append(f'<text x="52" y="167" fill="#c9d1d9" font-family="ui-monospace,SFMono-Regular,Menlo,Monaco,Consolas,monospace" font-size="10">{html.escape(footer)}</text>')

    legend_x = 690
    parts.append(f'<text x="{legend_x}" y="167" fill="#8b949e" font-family="ui-monospace,SFMono-Regular,Menlo,Monaco,Consolas,monospace" font-size="9">Less</text>')
    for i, color in enumerate(PALETTE):
        parts.append(f'<rect x="{legend_x + 28 + i * 15}" y="158" width="10" height="10" rx="2" fill="{color}"/>')
    parts.append(f'<text x="{legend_x + 108}" y="167" fill="#8b949e" font-family="ui-monospace,SFMono-Regular,Menlo,Monaco,Consolas,monospace" font-size="9">More</text>')
    parts.append("</svg>")

    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text("\\n".join(parts), encoding="utf-8")
    print(f"wrote {OUTPUT}")

if __name__ == "__main__":
    main()
