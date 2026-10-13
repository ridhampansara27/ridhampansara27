#!/usr/bin/env python3
"""Fetch the public GitHub contribution calendar and save normalized JSON."""
from __future__ import annotations

import json
import re
from collections import defaultdict
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

import requests
from bs4 import BeautifulSoup

USERNAME = "ridhampansara27"
URL = f"https://github.com/users/{USERNAME}/contributions"
OUTPUT = Path("data/contributions.json")
COUNT_RE = re.compile(r"([\d,]+)\s+contribution", re.I)

def parse_count(cell, tooltip_map: dict[str, str]) -> int:
    cell_id = cell.get("id", "")
    candidates = [
        cell.get("aria-label", ""),
        cell.get("data-count", ""),
        cell.get_text(" ", strip=True),
        tooltip_map.get(cell_id, ""),
    ]
    for value in candidates:
        text = str(value).strip()
        if not text:
            continue
        if text.isdigit():
            return int(text)
        if "no contribution" in text.lower():
            return 0
        match = COUNT_RE.search(text)
        if match:
            return int(match.group(1).replace(",", ""))
    return 0

def compute_stats(days: list[dict]) -> dict:
    if not days:
        return {"total": 0, "current_streak": 0, "longest_streak": 0, "best_day": None, "best_month": None}

    by_date = {date.fromisoformat(d["date"]): int(d["count"]) for d in days}
    ordered = sorted(by_date)
    total = sum(by_date.values())

    longest = run = 0
    for d in ordered:
        if by_date[d] > 0:
            run += 1
            longest = max(longest, run)
        else:
            run = 0

    today = date.today()
    cursor = min(today, ordered[-1])
    if cursor == today and by_date.get(cursor, 0) == 0:
        cursor -= timedelta(days=1)

    current = 0
    while by_date.get(cursor, 0) > 0:
        current += 1
        cursor -= timedelta(days=1)

    best_date = max(ordered, key=lambda d: by_date[d])
    months: dict[str, int] = defaultdict(int)
    for d, count in by_date.items():
        months[d.strftime("%Y-%m")] += count
    best_month_key = max(months, key=months.get)

    return {
        "total": total,
        "current_streak": current,
        "longest_streak": longest,
        "best_day": {"date": best_date.isoformat(), "count": by_date[best_date]},
        "best_month": {"month": best_month_key, "count": months[best_month_key]},
    }

def main() -> None:
    response = requests.get(
        URL,
        timeout=30,
        headers={
            "User-Agent": "ridham-profile-readme/1.0",
            "Accept-Language": "en-US,en;q=0.9",
        },
    )
    response.raise_for_status()
    soup = BeautifulSoup(response.text, "html.parser")

    tooltip_map = {}
    for tip in soup.select("tool-tip[for]"):
        target = tip.get("for")
        if target:
            tooltip_map[target] = tip.get_text(" ", strip=True)

    cells = soup.select("td[data-date], rect[data-date]")
    days = []
    for cell in cells:
        day = cell.get("data-date")
        if not day:
            continue
        try:
            level = int(cell.get("data-level", "0"))
        except (TypeError, ValueError):
            level = 0
        days.append({
            "date": day,
            "count": parse_count(cell, tooltip_map),
            "level": max(0, min(level, 4)),
        })

    if not days:
        raise RuntimeError("No contribution cells found; GitHub contribution markup may have changed")

    deduped = {d["date"]: d for d in days}
    normalized = [deduped[k] for k in sorted(deduped)]
    payload = {
        "username": USERNAME,
        "source": URL,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "days": normalized,
        "stats": compute_stats(normalized),
    }

    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    print(f"wrote {OUTPUT} with {len(normalized)} days")

if __name__ == "__main__":
    main()
