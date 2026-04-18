#!/usr/bin/env python3
"""
Friction analyzer — reads Claude Code's native telemetry to surface
recurring friction patterns.

Reads from:
  ~/.claude/usage-data/facets/*.json    (friction classification, outcomes)
  ~/.claude/usage-data/session-meta/*.json (tool errors, duration, interruptions)

Usage:
    python3 analyzer.py                 # print friction summary as JSON
    python3 analyzer.py --category X    # filter to a specific friction category
    python3 analyzer.py --days N        # lookback window (default 28)
"""

import json
import sys
import os
from datetime import datetime, timedelta
from pathlib import Path
from collections import Counter, defaultdict

USAGE_DATA = Path.home() / ".claude" / "usage-data"
FACETS_DIR = USAGE_DATA / "facets"
META_DIR = USAGE_DATA / "session-meta"
DEFAULT_WINDOW_DAYS = 28


def load_session(session_id: str) -> dict | None:
    """Load session-meta for a given session ID."""
    path = META_DIR / f"{session_id}.json"
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text())
    except (json.JSONDecodeError, OSError):
        return None


def load_facets(days: int = DEFAULT_WINDOW_DAYS, category: str | None = None) -> list[dict]:
    """Load all facets with friction within the lookback window."""
    if not FACETS_DIR.exists():
        return []

    cutoff = datetime.now() - timedelta(days=days)
    results = []

    for path in FACETS_DIR.glob("*.json"):
        try:
            facet = json.loads(path.read_text())
        except (json.JSONDecodeError, OSError):
            continue

        if not facet.get("friction_counts"):
            continue

        # Filter by category if specified
        if category and category not in facet.get("friction_counts", {}):
            continue

        # Check date via paired session-meta
        session_id = facet.get("session_id", path.stem)
        meta = load_session(session_id)
        if meta:
            try:
                start = datetime.fromisoformat(meta["start_time"].replace("Z", "+00:00")).replace(tzinfo=None)
                if start < cutoff:
                    continue
            except (KeyError, ValueError):
                pass

        results.append({
            "session_id": session_id,
            "goal": facet.get("underlying_goal", ""),
            "outcome": facet.get("outcome", ""),
            "helpfulness": facet.get("claude_helpfulness", ""),
            "session_type": facet.get("session_type", ""),
            "friction_counts": facet.get("friction_counts", {}),
            "friction_detail": facet.get("friction_detail", ""),
            "summary": facet.get("brief_summary", ""),
            "meta": {
                "start_time": meta.get("start_time", ""),
                "duration_minutes": meta.get("duration_minutes", 0),
                "tool_errors": meta.get("tool_errors", 0),
                "tool_error_categories": meta.get("tool_error_categories", {}),
                "user_interruptions": meta.get("user_interruptions", 0),
                "project_path": meta.get("project_path", ""),
            } if meta else None,
        })

    # Sort by date (most recent first)
    results.sort(key=lambda r: (r["meta"] or {}).get("start_time", ""), reverse=True)
    return results


def summarize(sessions: list[dict]) -> dict:
    """Aggregate friction data into a summary."""
    category_counts = Counter()
    category_details = defaultdict(list)
    outcome_counts = Counter()

    for s in sessions:
        outcome_counts[s["outcome"]] += 1
        for cat, count in s["friction_counts"].items():
            category_counts[cat] += count
            if s["friction_detail"]:
                category_details[cat].append({
                    "detail": s["friction_detail"],
                    "goal": s["goal"][:150],
                    "outcome": s["outcome"],
                    "session_id": s["session_id"],
                })

    # Build ranked categories with their recent examples
    ranked = []
    for cat, count in category_counts.most_common():
        details = category_details.get(cat, [])
        ranked.append({
            "category": cat,
            "count": count,
            "sessions": len(details),
            "recent_examples": details[:5],
        })

    return {
        "total_sessions_with_friction": len(sessions),
        "outcome_distribution": dict(outcome_counts),
        "friction_categories": ranked,
    }


if __name__ == "__main__":
    days = DEFAULT_WINDOW_DAYS
    category = None

    args = sys.argv[1:]
    i = 0
    while i < len(args):
        if args[i] == "--days" and i + 1 < len(args):
            days = int(args[i + 1])
            i += 2
        elif args[i] == "--category" and i + 1 < len(args):
            category = args[i + 1]
            i += 2
        else:
            i += 1

    sessions = load_facets(days=days, category=category)
    if not sessions:
        print(json.dumps({"total_sessions_with_friction": 0, "friction_categories": []}))
    else:
        print(json.dumps(summarize(sessions), indent=2))
