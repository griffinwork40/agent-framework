"""
agent-afk session facets as a friction source.

agent-afk derives one SessionFacet JSON per session into
<agent-framework>/facets/<session_id>.json (see agent-afk
src/agent/facets/schema.ts and getFacetCacheDir() in src/paths.ts). Unlike
Claude Code's usage-data facets, these are written on this machine for every
AFK session, so they are the primary source of *goal* context for friction.

Contract:
  - Facet friction_counts are keyed by bare tool name ({"bash": 3}) and carry
    no failure class. They are mapped to `tool_error:<tool>:unclassified`,
    which ranks with the low-confidence `:plain` residue in analyzer.py.
  - When a session also has a witness trace, the trace's counts are strictly
    richer (they carry :timeout/:truncated/:slow), so the facet contributes
    only goal / summary / outcome and never adds counts. This prevents the
    same tool error being counted twice.
  - Fresh (non-daemon) sessions label their witness trace dir with a random
    UUID, not the session id, so an id-only join misses most traces. The
    session ledger (<state>/sessions/<id>/events.jsonl, first line kind:"meta")
    records `traceLabel`, the durable id->label bridge; enrichment joins on it.
  - Directories are resolved at call time (not import time) so tests and
    callers can redirect it via env without reloading the module.
"""

import json
import os
from datetime import datetime, timedelta
from pathlib import Path


def resolve_afk_facets_dir() -> Path:
    """AFK_FACETS_DIR > $AFK_FRAMEWORK_DIR/facets > ($AFK_HOME or ~/.afk)/agent-framework/facets.

    Mirrors getAgentFrameworkDir() + getFacetCacheDir() in agent-afk src/paths.ts.
    """
    override = os.environ.get("AFK_FACETS_DIR")
    if override:
        return Path(override)
    framework = os.environ.get("AFK_FRAMEWORK_DIR")
    if framework:
        return Path(framework) / "facets"
    home = Path(os.environ.get("AFK_HOME") or (Path.home() / ".afk"))
    return home / "agent-framework" / "facets"


def resolve_sessions_dir() -> Path:
    """$AFK_STATE_DIR/sessions > ($AFK_HOME or ~/.afk)/state/sessions (agent-afk src/paths.ts)."""
    state = os.environ.get("AFK_STATE_DIR")
    if state:
        return Path(state) / "sessions"
    home = Path(os.environ.get("AFK_HOME") or (Path.home() / ".afk"))
    return home / "state" / "sessions"


def trace_label_for(session_id: str, sessions_dir: Path) -> str | None:
    """Witness trace label recorded on the session ledger's meta line, or None."""
    try:
        with open(sessions_dir / session_id / "events.jsonl") as fh:
            meta = json.loads(fh.readline())
    except (OSError, json.JSONDecodeError):
        return None
    label = meta.get("traceLabel") if isinstance(meta, dict) and meta.get("kind") == "meta" else None
    return label if isinstance(label, str) and label else None


def _parse_ts(value: str):
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00")).replace(tzinfo=None)
    except (AttributeError, ValueError):
        return None


def _matches(counts: dict, category) -> bool:
    return category is None or any(k == category or k.startswith(category + ":") for k in counts)


def load_afk_facets(
    days: int, cap: int, facets_dir: Path | None = None, sessions_dir: Path | None = None,
) -> dict:
    """Return {session_id: record} for every AFK facet whose start_time is in the window.

    Facets without friction are kept too: they still supply the goal for a
    session whose friction was found in its witness trace.
    """
    root = facets_dir or resolve_afk_facets_dir()
    ledgers = sessions_dir or resolve_sessions_dir()
    if not root.exists():
        return {}
    cutoff = datetime.now() - timedelta(days=days)
    out = {}
    for path in root.glob("*.json"):
        try:
            facet = json.loads(path.read_text())
        except (json.JSONDecodeError, OSError):
            continue
        if not isinstance(facet, dict) or facet.get("derived_from", "afk-session") != "afk-session":
            continue
        start_time = facet.get("start_time") or ""
        start = _parse_ts(start_time)
        if start is not None and start < cutoff:
            continue
        raw = facet.get("friction_counts") or {}
        counts = {
            f"tool_error:{tool}:unclassified": min(int(n), cap)
            for tool, n in raw.items()
            if isinstance(n, (int, float)) and n > 0
        }
        session_id = facet.get("session_id") or path.stem
        out[session_id] = {
            "session_id": session_id,
            "goal": facet.get("underlying_goal", "") or "",
            "outcome": facet.get("outcome", "") or "",
            "helpfulness": "",
            "session_type": facet.get("session_type", "") or "",
            "friction_counts": counts,
            # summarize() drops examples with an empty detail, so never leave it blank.
            "friction_detail": facet.get("friction_detail", "")
            or ", ".join(f"{k} x{v}" for k, v in counts.items()),
            "summary": facet.get("brief_summary", "") or "",
            "meta": {"start_time": start_time, "tool_errors": facet.get("tool_errors", 0)},
            "trace_label": trace_label_for(session_id, ledgers),
        }
    return out


def enrich_with_afk_facets(sessions: list, afk: dict, category=None) -> list:
    """Attach AFK goal context to existing sessions; add facet-only sessions with friction."""
    by_id = {s["session_id"]: s for s in sessions}
    for session_id, rec in afk.items():
        rec = dict(rec)
        label = rec.pop("trace_label", None)
        existing = by_id.get(session_id)
        if existing is None and label and label != session_id and label in by_id:
            # Re-key the witness-only session to its real session id so the
            # example is resolvable with get_facet / the session store.
            existing = by_id.pop(label)
            existing["session_id"] = session_id
            by_id[session_id] = existing
        if existing is not None:
            if not existing.get("goal"):
                existing["goal"] = rec["goal"]
            if not existing.get("summary"):
                existing["summary"] = rec["summary"]
            # Witness outcomes are only "completed"/"aborted"; keep a real abort,
            # otherwise prefer the facet's richer outcome classification.
            if existing.get("outcome") in ("", "completed") and rec["outcome"]:
                existing["outcome"] = rec["outcome"]
            continue
        if rec["friction_counts"] and _matches(rec["friction_counts"], category):
            by_id[session_id] = rec
    return list(by_id.values())
