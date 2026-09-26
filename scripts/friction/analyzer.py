#!/usr/bin/env python3
"""
Friction analyzer — reads session telemetry to surface recurring
friction patterns.

Sources, merged per session id:
  1. agent-afk session facets: <agent-framework>/facets/*.json (goal, outcome,
     unclassified tool-error counts). See afk_facets.py.
  2. agent-afk witness traces: ~/.afk/state/witness/*/trace.jsonl (tool errors
     subclassed by failure class, subagent failures, aborts, hook blocks).
  3. Claude Code usage-data facets: <usage-data>/facets/*.json and
     <usage-data>/session-meta/*.json (legacy; absent on AFK-only machines).

The usage-data root is resolved in priority order:
  1. $USAGE_DATA_DIR env var (caller override)
  2. ~/.afk/usage-data/ if it exists
  3. ~/.claude/usage-data/ (legacy default — facet data lives here today
     since Claude Code is the only host that emits facets)

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

from afk_facets import enrich_with_afk_facets, load_afk_facets


def _resolve_usage_data_dir() -> Path:
    """Resolve the usage-data root: env > AFK > legacy default."""
    override = os.environ.get("USAGE_DATA_DIR")
    if override:
        return Path(override)
    afk_path = Path.home() / ".afk" / "usage-data"
    if afk_path.exists():
        return afk_path
    return Path.home() / ".claude" / "usage-data"


USAGE_DATA = _resolve_usage_data_dir()
FACETS_DIR = USAGE_DATA / "facets"
META_DIR = USAGE_DATA / "session-meta"
DEFAULT_WINDOW_DAYS = 28


def _resolve_witness_dir() -> Path:
    if os.environ.get("AFK_WITNESS_DIR"):
        return Path(os.environ["AFK_WITNESS_DIR"])
    home = Path(os.environ.get("AFK_HOME") or (Path.home() / ".afk"))
    return home / "state" / "witness"


WITNESS_DIR = _resolve_witness_dir()
PER_SESSION_CAP = 5
TIMEOUT_MS = 120_000  # bash tool hard-timeout default; a non-zero return at/after this is ~certainly a timeout
SLOW_MS = 30_000      # pathologically slow but the call still returned
# Tools whose normal runtime exceeds the bash thresholds above (subagent dispatch,
# waits on an external condition or a human).
# Median failed agent/compose call observed at ~242 s, i.e. ordinary work, not a hang.
LONG_RUNNING_TOOLS = frozenset({"agent", "compose", "skill", "wait_for", "ask_question"})


def _error_subclass(p) -> str:
    """Stable failure-class suffix from fields ALREADY present in the witness error event.
    Precedence: truncated > timeout > slow > plain. ':plain' is the residue the trace
    cannot separate from a benign non-zero exit — no exit code or command text is captured."""
    if p.get("truncated"):
        return "truncated"
    if p.get("name") in LONG_RUNNING_TOOLS:
        # A subagent dispatch routinely runs for minutes; its duration says nothing
        # about a timeout, so it never earns the high-confidence duration classes.
        return "plain"
    dur = p.get("durationMs") or 0
    if dur >= TIMEOUT_MS:
        return "timeout"
    if dur >= SLOW_MS:
        return "slow"
    return "plain"


def _category_match(counts, category) -> bool:
    """`--category tool_error:bash` matches an exact key OR any ':' subclass of it, so the
    pre-subclass filter behavior is preserved against the now-subclassed witness keys."""
    return any(k == category or k.startswith(category + ":") for k in counts)


def _categorize(kind, p):
    if kind == "tool_call" and p.get("phase") == "completed" and p.get("isError") is True:
        return f"tool_error:{p.get('name','?')}:{_error_subclass(p)}", ""
    if kind == "subagent_lifecycle" and p.get("transition") == "failed":
        return f"subagent_fail:{p.get('errorClass','?')}", (p.get("errorMessage") or "")[:80]
    if kind == "abort":
        return f"abort:{p.get('origin','?')}", (p.get("reason") or "")[:80]
    if kind == "closure" and p.get("reason") not in (None, "model_end_turn"):
        return f"closure:{p.get('reason')}", ""
    if kind == "hook_decision" and p.get("decision") == "block":
        return f"hook_block:{p.get('blockedTool','?')}", (p.get("reason") or "")[:80]
    return None


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


def load_witness_friction(days=DEFAULT_WINDOW_DAYS, category=None):
    if not WITNESS_DIR.exists():
        return []
    cutoff = datetime.now() - timedelta(days=days)
    results = []
    for path in WITNESS_DIR.glob("*/trace.jsonl"):
        raw, notes, first_ts, outcome = Counter(), [], None, "completed"
        try:
            lines = path.read_text().splitlines()
        except OSError:
            continue
        for line in lines:
            try:
                ev = json.loads(line)
            except json.JSONDecodeError:
                continue
            first_ts = first_ts or ev.get("ts")
            c = _categorize(ev.get("kind", ""), ev.get("payload") or {})
            if c:
                raw[c[0]] += 1
                if c[1]:
                    notes.append(c[1])
                if c[0].startswith(("abort:", "closure:")):
                    outcome = "aborted"
        if not raw:
            continue
        if first_ts:
            try:
                start = datetime.fromisoformat(first_ts.replace("Z", "+00:00")).replace(tzinfo=None)
                if start < cutoff:
                    continue
            except ValueError:
                pass
        fc = {k: min(v, PER_SESSION_CAP) for k, v in raw.items()}
        if category and not _category_match(fc, category):
            continue
        top = ", ".join(f"{k} x{v}" for k, v in raw.most_common(3))
        detail = (top + ("; " + "; ".join(notes[:2]) if notes else ""))[:200]
        results.append({
            "session_id": path.parent.name, "goal": "", "outcome": outcome,
            "helpfulness": "", "session_type": "trace", "friction_counts": fc,
            "friction_detail": detail, "summary": "",
            "meta": {"start_time": first_ts or "", "tool_errors": sum(raw.values())},
        })
    results.sort(key=lambda r: (r["meta"] or {}).get("start_time", ""), reverse=True)
    return results


def merge_sessions(facets, witness):
    by_id = {s["session_id"]: s for s in facets}
    for w in witness:
        b = by_id.get(w["session_id"])
        if b:
            fc = dict(b.get("friction_counts", {}))
            for k, v in w["friction_counts"].items():
                fc[k] = fc.get(k, 0) + v
            b["friction_counts"] = fc
            if w["friction_detail"]:
                b["friction_detail"] = (b.get("friction_detail", "") + " | trace: " + w["friction_detail"]).strip(" |")
        else:
            by_id[w["session_id"]] = w
    return list(by_id.values())


# "unclassified" = AFK facet tool-error counts with no failure class; as weak as :plain.
_SUBCLASS_PRIORITY = {"truncated": 3, "timeout": 3, "slow": 2, "plain": 0, "unclassified": 0}


def _friction_priority(category: str) -> int:
    """Forge-ranking weight. High-confidence tool-error subclasses (timeout/truncated/slow)
    outrank the low-confidence ':plain' residue; every other category is normal (1, > plain)."""
    parts = category.split(":")
    if parts[0] == "tool_error" and len(parts) >= 3:
        return _SUBCLASS_PRIORITY.get(parts[-1], 1)
    return 1


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

    # Forge ranking: high-confidence failure classes first, then by frequency.
    # most_common() above already orders by count and sort() is stable, so this
    # promotes :timeout/:truncated/:slow above the low-confidence :plain residue
    # while preserving count order within each confidence tier.
    ranked.sort(key=lambda r: (-_friction_priority(r["category"]), -r["count"]))

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

    sessions = merge_sessions(
        load_facets(days=days, category=category),
        load_witness_friction(days=days, category=category),
    )
    sessions = enrich_with_afk_facets(
        sessions, load_afk_facets(days=days, cap=PER_SESSION_CAP), category=category,
    )
    # Most recent first, so each category's recent_examples[:5] really are recent.
    sessions.sort(key=lambda r: (r.get("meta") or {}).get("start_time", ""), reverse=True)
    if not sessions:
        print(json.dumps({"total_sessions_with_friction": 0, "friction_categories": []}))
    else:
        print(json.dumps(summarize(sessions), indent=2))
