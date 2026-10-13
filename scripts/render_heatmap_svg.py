#!/usr/bin/env python3
"""Render a polished animated 53-week GitHub activity SVG."""
from __future__ import annotations

import html
import json
from datetime import date, timedelta
from pathlib import Path

INPUT = Path("data/contributions.json")
OUTPUT = Path("assets/github-activity.svg")
PALETTE = ["#161b22", "#0e4429", "#006d32", "#26a641", "#39d353"]

def sunday_index(d: date) -> int:
    return (d.weekday() + 1) % 7

def main() -> None:
    payload = json.loads(INPUT.read_text(encoding="utf-8"))
    days = payload.get("days", [])
    by_date = {date.fromisoformat(d["date"]): d for d in days}
    stats = payload.get("stats", {})

    width, height = 920, 235
    left, top = 84, 90
    size, gap, weeks = 10, 4, 53
    pitch = size + gap

    last = max(by_date) if by_date else date.today()
    week_end = last + timedelta(days=(6 - sunday_index(last)))
    start = week_end - timedelta(days=(weeks * 7 - 1))

    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}" role="img" aria-labelledby="title desc">',
        '<title id="title">GitHub activity for Ridham Pansara</title>',
        '<desc id="desc">Live contribution activity for the last year, refreshed daily from public GitHub data.</desc>',
        '<defs><linearGradient id="bg" x1="0" y1="0" x2="1" y2="1"><stop offset="0%" stop-color="#0d1117"/><stop offset="100%" stop-color="#101722"/></linearGradient></defs>',
        '<rect x="1" y="1" width="918" height="233" rx="18" fill="url(#bg)" stroke="#30363d"/>',
        '<g font-family="Inter,Segoe UI,Arial,sans-serif">',
        '<text x="28" y="36" fill="#f0f6fc" font-size="18" font-weight="700">GitHub activity</text>',
        '<text x="28" y="57" fill="#8b949e" font-size="12">Automatically refreshed from public contribution data</text>',
    ]

    total = int(stats.get("total", 0))
    current = int(stats.get("current_streak", 0))
    longest = int(stats.get("longest_streak", 0))
    cards = [
        (620, "#111d2c", "#1f4b73", "#79c0ff", f"{total:,}", "CONTRIBUTIONS"),
        (712, "#14221a", "#285d38", "#56d364", f"{current}d", "CURRENT STREAK"),
        (804, "#20162f", "#5b3f83", "#c4a7ff", f"{longest}d", "LONGEST STREAK"),
    ]
    for x, fill, stroke, fg, value, label in cards:
        parts.extend([
            f'<rect x="{x}" y="20" width="80" height="40" rx="10" fill="{fill}" stroke="{stroke}"/>',
            f'<text x="{x+40}" y="38" text-anchor="middle" fill="{fg}" font-size="15" font-weight="700">{html.escape(value)}</text>',
            f'<text x="{x+40}" y="52" text-anchor="middle" fill="#8b949e" font-size="9">{label}</text>',
        ])

    seen = set()
    for week in range(weeks):
        d = start + timedelta(days=week * 7)
        if d.day <= 7 and (d.year, d.month) not in seen:
            seen.add((d.year, d.month))
            parts.append(f'<text x="{left + week*pitch}" y="80" fill="#8b949e" font-size="10">{d.strftime("%b")}</text>')

    for label, row in [("Mon", 1), ("Wed", 3), ("Fri", 5)]:
        parts.append(f'<text x="47" y="{top + row*pitch + 9}" fill="#8b949e" font-size="9">{label}</text>')

    for week in range(weeks):
        for row in range(7):
            d = start + timedelta(days=week * 7 + row)
            info = by_date.get(d, {"count": 0, "level": 0})
            level = max(0, min(4, int(info.get("level", 0))))
            count = int(info.get("count", 0))
            x, y = left + week * pitch, top + row * pitch
            delay = min(1.5, 0.015 + week * 0.012 + row * 0.006)
            parts.append(
                f'<rect x="{x}" y="{y}" width="{size}" height="{size}" rx="2" fill="{PALETTE[level]}" opacity="0">'
                f'<title>{html.escape(d.isoformat())}: {count} contributions</title>'
                f'<animate attributeName="opacity" from="0" to="1" dur=".22s" begin="{delay:.3f}s" fill="freeze"/>'
                '</rect>'
            )

    best_month = (stats.get("best_month") or {}).get("month", "—")
    best_day = stats.get("best_day") or {}
    footer = f'Best month: {best_month} · Best day: {best_day.get("date", "—")} ({best_day.get("count", 0)})'
    parts.append(f'<text x="28" y="215" fill="#8b949e" font-size="11">{html.escape(footer)}</text>')
    parts.append('<text x="785" y="215" fill="#8b949e" font-size="10">Less</text>')
    for i, color in enumerate(PALETTE):
        parts.append(f'<rect x="{814+i*15}" y="206" width="10" height="10" rx="2" fill="{color}"/>')
    parts.append('<text x="894" y="215" text-anchor="end" fill="#8b949e" font-size="10">More</text>')
    parts.append('</g></svg>')

    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text("\n".join(parts), encoding="utf-8")
    print(f"wrote {OUTPUT}")

if __name__ == "__main__":
    main()
