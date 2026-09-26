"""
Tests for the witness-trace integration in analyzer.py.
Covers: _categorize(), per-session cap, load_witness_friction(), merge_sessions().
"""
import json
import os
import sys
import tempfile
from collections import Counter
from datetime import datetime
from pathlib import Path

import pytest

# Ensure we import the analyzer module directly, even when pytest is run from
# a different cwd.
sys.path.insert(0, str(Path(__file__).parent))
import importlib
import analyzer as _base_module  # noqa: E402 – used for reload after env patch


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def make_trace(tmp_path: Path, session_id: str, events: list[dict]) -> Path:
    """Write a trace.jsonl for a synthetic session and return its path."""
    d = tmp_path / session_id
    d.mkdir(parents=True, exist_ok=True)
    p = d / "trace.jsonl"
    p.write_text("\n".join(json.dumps(e) for e in events))
    return p


def now_ts() -> str:
    return datetime.now().isoformat() + "Z"


def error_event(i: int, name: str = "bash") -> dict:
    return {
        "ts": now_ts(), "seq": i, "kind": "tool_call",
        "payload": {"phase": "completed", "name": name,
                    "isError": True, "truncated": False,
                    "durationMs": 500, "resultBytes": 10},
    }


def error_event_ex(i: int, name: str = "bash", truncated: bool = False,
                   duration_ms: int = 500) -> dict:
    """error_event with explicit truncated/durationMs for subclass fingerprint tests."""
    return {
        "ts": now_ts(), "seq": i, "kind": "tool_call",
        "payload": {"phase": "completed", "name": name, "isError": True,
                    "truncated": truncated, "durationMs": duration_ms,
                    "resultBytes": 10},
    }


def closure_event(reason: str = "abort") -> dict:
    return {
        "ts": now_ts(), "seq": 99, "kind": "closure",
        "payload": {"reason": reason, "finalTurnCount": 1,
                    "finalCostUsd": 0.0, "finalTokens": {}},
    }


def abort_event(origin: str = "user_signal", reason: str = "cancelled") -> dict:
    return {
        "ts": now_ts(), "seq": 50, "kind": "abort",
        "payload": {"origin": origin, "reason": reason},
    }


def subagent_fail_event(cls: str = "TypeError", msg: str = "terminated") -> dict:
    return {
        "ts": now_ts(), "seq": 60, "kind": "subagent_lifecycle",
        "payload": {"transition": "failed", "errorClass": cls, "errorMessage": msg},
    }


def hook_block_event(tool: str = "bash", reason: str = "denied") -> dict:
    return {
        "ts": now_ts(), "seq": 70, "kind": "hook_decision",
        "payload": {"decision": "block", "blockedTool": tool, "reason": reason},
    }


# ---------------------------------------------------------------------------
# _categorize() unit tests
# ---------------------------------------------------------------------------

class TestCategorize:
    def test_tool_error_bash(self):
        from analyzer import _categorize
        cat, note = _categorize("tool_call", {
            "phase": "completed", "name": "bash", "isError": True,
        })
        assert cat == "tool_error:bash:plain"
        assert note == ""

    def test_tool_error_missing_isError(self):
        from analyzer import _categorize
        result = _categorize("tool_call", {"phase": "completed", "name": "bash"})
        assert result is None

    def test_tool_error_isError_false(self):
        from analyzer import _categorize
        result = _categorize("tool_call", {"phase": "completed", "name": "bash", "isError": False})
        assert result is None

    def test_subagent_fail(self):
        from analyzer import _categorize
        cat, note = _categorize("subagent_lifecycle", {
            "transition": "failed", "errorClass": "TypeError", "errorMessage": "terminated",
        })
        assert cat == "subagent_fail:TypeError"
        assert "terminated" in note

    def test_subagent_fail_long_message_truncated(self):
        from analyzer import _categorize
        long_msg = "x" * 200
        _, note = _categorize("subagent_lifecycle", {
            "transition": "failed", "errorClass": "Error", "errorMessage": long_msg,
        })
        assert len(note) == 80

    def test_abort(self):
        from analyzer import _categorize
        cat, note = _categorize("abort", {"origin": "user_signal", "reason": "cancelled"})
        assert cat == "abort:user_signal"
        assert "cancelled" in note

    def test_closure_abort(self):
        from analyzer import _categorize
        cat, note = _categorize("closure", {"reason": "abort"})
        assert cat == "closure:abort"
        assert note == ""

    def test_closure_model_end_turn_ignored(self):
        from analyzer import _categorize
        result = _categorize("closure", {"reason": "model_end_turn"})
        assert result is None

    def test_closure_none_reason_ignored(self):
        from analyzer import _categorize
        result = _categorize("closure", {"reason": None})
        assert result is None

    def test_hook_block(self):
        from analyzer import _categorize
        cat, note = _categorize("hook_decision", {
            "decision": "block", "blockedTool": "edit_file", "reason": "denied",
        })
        assert cat == "hook_block:edit_file"
        assert "denied" in note

    def test_unknown_kind_ignored(self):
        from analyzer import _categorize
        result = _categorize("some_other_kind", {"isError": True})
        assert result is None

    def test_missing_payload_fields_default_to_question_mark(self):
        from analyzer import _categorize
        cat, _ = _categorize("tool_call", {"phase": "completed", "isError": True})
        assert cat == "tool_error:?:plain"


# ---------------------------------------------------------------------------
# per-session cap
# ---------------------------------------------------------------------------

class TestPerSessionCap:
    def test_cap_applied(self, tmp_path):
        """7 bash errors → capped to PER_SESSION_CAP=5 in friction_counts."""
        make_trace(tmp_path, "sess_cap", [error_event(i) for i in range(7)] + [closure_event()])
        os.environ["AFK_WITNESS_DIR"] = str(tmp_path)
        # Reload to pick up new env
        import importlib
        import analyzer as mod
        importlib.reload(mod)
        results = mod.load_witness_friction()
        os.environ.pop("AFK_WITNESS_DIR", None)
        importlib.reload(mod)  # restore default

        assert len(results) == 1
        fc = results[0]["friction_counts"]
        assert fc.get("tool_error:bash:plain") == 5  # capped (durationMs=500 ⇒ :plain)

    def test_raw_count_shown_in_detail(self, tmp_path):
        """The friction_detail string reflects raw (pre-cap) counts for transparency."""
        make_trace(tmp_path, "sess_raw", [error_event(i) for i in range(7)])
        os.environ["AFK_WITNESS_DIR"] = str(tmp_path)
        import importlib
        import analyzer as mod
        importlib.reload(mod)
        results = mod.load_witness_friction()
        os.environ.pop("AFK_WITNESS_DIR", None)
        importlib.reload(mod)

        assert results[0]["friction_detail"].startswith("tool_error:bash:plain x7")


# ---------------------------------------------------------------------------
# load_witness_friction()
# ---------------------------------------------------------------------------

class TestLoadWitnessFriction:
    def test_three_sessions(self, tmp_path):
        """3 sessions × 7 errors → sessions:3, capped counts sum to 15."""
        for sid in ("s1", "s2", "s3"):
            make_trace(
                tmp_path, sid,
                [error_event(i) for i in range(7)] + [closure_event()],
            )
        os.environ["AFK_WITNESS_DIR"] = str(tmp_path)
        import importlib
        import analyzer as mod
        importlib.reload(mod)
        results = mod.load_witness_friction()
        os.environ.pop("AFK_WITNESS_DIR", None)
        importlib.reload(mod)

        assert len(results) == 3
        total_bash = sum(r["friction_counts"].get("tool_error:bash:plain", 0) for r in results)
        assert total_bash == 15  # 3 × min(7, 5)

    def test_empty_dir_returns_empty_list(self, tmp_path):
        witness_dir = tmp_path / "empty_witness"
        witness_dir.mkdir()
        os.environ["AFK_WITNESS_DIR"] = str(witness_dir)
        import importlib
        import analyzer as mod
        importlib.reload(mod)
        results = mod.load_witness_friction()
        os.environ.pop("AFK_WITNESS_DIR", None)
        importlib.reload(mod)

        assert results == []

    def test_nonexistent_dir_returns_empty_list(self, tmp_path):
        os.environ["AFK_WITNESS_DIR"] = str(tmp_path / "does_not_exist")
        import importlib
        import analyzer as mod
        importlib.reload(mod)
        results = mod.load_witness_friction()
        os.environ.pop("AFK_WITNESS_DIR", None)
        importlib.reload(mod)

        assert results == []

    def test_category_filter(self, tmp_path):
        """--category should exclude sessions that lack that category."""
        # s1 has only tool errors; s2 has only subagent_fail
        make_trace(tmp_path, "s_tool", [error_event(0)])
        make_trace(tmp_path, "s_sub", [subagent_fail_event()])
        os.environ["AFK_WITNESS_DIR"] = str(tmp_path)
        import importlib
        import analyzer as mod
        importlib.reload(mod)
        results = mod.load_witness_friction(category="tool_error:bash")
        os.environ.pop("AFK_WITNESS_DIR", None)
        importlib.reload(mod)

        assert len(results) == 1
        assert results[0]["session_id"] == "s_tool"

    def test_malformed_lines_skipped(self, tmp_path):
        """A trace with some malformed JSON lines still produces results for valid lines."""
        d = tmp_path / "sess_bad"
        d.mkdir()
        lines = [
            "NOT VALID JSON",
            json.dumps(error_event(0)),
            "{broken",
            json.dumps(error_event(1)),
        ]
        (d / "trace.jsonl").write_text("\n".join(lines))

        os.environ["AFK_WITNESS_DIR"] = str(tmp_path)
        import importlib
        import analyzer as mod
        importlib.reload(mod)
        results = mod.load_witness_friction()
        os.environ.pop("AFK_WITNESS_DIR", None)
        importlib.reload(mod)

        assert len(results) == 1
        assert results[0]["friction_counts"]["tool_error:bash:plain"] == 2

    def test_outcome_aborted_on_closure(self, tmp_path):
        make_trace(tmp_path, "sess_ab", [error_event(0), closure_event("abort")])
        os.environ["AFK_WITNESS_DIR"] = str(tmp_path)
        import importlib
        import analyzer as mod
        importlib.reload(mod)
        results = mod.load_witness_friction()
        os.environ.pop("AFK_WITNESS_DIR", None)
        importlib.reload(mod)

        assert results[0]["outcome"] == "aborted"

    def test_session_type_is_trace(self, tmp_path):
        make_trace(tmp_path, "sess_ty", [error_event(0)])
        os.environ["AFK_WITNESS_DIR"] = str(tmp_path)
        import importlib
        import analyzer as mod
        importlib.reload(mod)
        results = mod.load_witness_friction()
        os.environ.pop("AFK_WITNESS_DIR", None)
        importlib.reload(mod)

        assert results[0]["session_type"] == "trace"


# ---------------------------------------------------------------------------
# merge_sessions()
# ---------------------------------------------------------------------------

class TestMergeSessions:
    def _make_facet(self, sid: str, counts: dict, detail: str = "") -> dict:
        return {
            "session_id": sid, "goal": "g", "outcome": "completed",
            "helpfulness": "high", "session_type": "interactive",
            "friction_counts": counts, "friction_detail": detail,
            "summary": "s", "meta": None,
        }

    def _make_witness(self, sid: str, counts: dict, detail: str = "") -> dict:
        return {
            "session_id": sid, "goal": "", "outcome": "completed",
            "helpfulness": "", "session_type": "trace",
            "friction_counts": counts, "friction_detail": detail,
            "summary": "", "meta": {"start_time": now_ts(), "tool_errors": 1},
        }

    def test_dedup_same_id_merges_counts(self):
        from analyzer import merge_sessions
        facets = [self._make_facet("s1", {"tool_error:bash": 2})]
        witness = [self._make_witness("s1", {"tool_error:bash": 3, "closure:abort": 1})]
        merged = merge_sessions(facets, witness)
        assert len(merged) == 1
        fc = merged[0]["friction_counts"]
        assert fc["tool_error:bash"] == 5
        assert fc["closure:abort"] == 1

    def test_new_witness_session_added(self):
        from analyzer import merge_sessions
        facets = [self._make_facet("s_facet", {"tool_error:bash": 1})]
        witness = [self._make_witness("s_witness", {"closure:abort": 1})]
        merged = merge_sessions(facets, witness)
        assert len(merged) == 2
        ids = {r["session_id"] for r in merged}
        assert "s_facet" in ids
        assert "s_witness" in ids

    def test_detail_concatenated(self):
        from analyzer import merge_sessions
        facets = [self._make_facet("s1", {"tool_error:bash": 1}, detail="existing")]
        witness = [self._make_witness("s1", {"tool_error:bash": 1}, detail="from trace")]
        merged = merge_sessions(facets, witness)
        assert "existing" in merged[0]["friction_detail"]
        assert "from trace" in merged[0]["friction_detail"]

    def test_empty_both(self):
        from analyzer import merge_sessions
        assert merge_sessions([], []) == []

    def test_only_witness(self):
        from analyzer import merge_sessions
        witness = [self._make_witness("s1", {"closure:abort": 2})]
        merged = merge_sessions([], witness)
        assert len(merged) == 1
        assert merged[0]["session_id"] == "s1"

    def test_only_facets(self):
        from analyzer import merge_sessions
        facets = [self._make_facet("s1", {"tool_error:bash": 3})]
        merged = merge_sessions(facets, [])
        assert len(merged) == 1
        assert merged[0]["session_type"] == "interactive"


# ---------------------------------------------------------------------------
# tool-error subclass fingerprints (Patch A: truncated / timeout / slow / plain)
# ---------------------------------------------------------------------------

class TestToolErrorSubclasses:
    """_categorize() splits tool errors into stable subclasses from trace-present fields."""

    def test_truncated(self):
        from analyzer import _categorize
        cat, note = _categorize("tool_call", {
            "phase": "completed", "name": "bash", "isError": True,
            "truncated": True, "durationMs": 5,
        })
        assert cat == "tool_error:bash:truncated"
        assert note == ""

    def test_truncated_beats_timeout(self):
        """truncated has highest precedence even when duration is in the timeout range."""
        from analyzer import _categorize
        cat, _ = _categorize("tool_call", {
            "phase": "completed", "name": "bash", "isError": True,
            "truncated": True, "durationMs": 999_999,
        })
        assert cat == "tool_error:bash:truncated"

    def test_timeout(self):
        from analyzer import _categorize
        cat, _ = _categorize("tool_call", {
            "phase": "completed", "name": "bash", "isError": True,
            "truncated": False, "durationMs": 120_000,
        })
        assert cat == "tool_error:bash:timeout"

    def test_timeout_lower_boundary(self):
        """>=120000 ⇒ timeout; 119999 ⇒ slow."""
        from analyzer import _categorize
        at, _ = _categorize("tool_call", {"phase": "completed", "name": "bash",
                                          "isError": True, "durationMs": 120_000})
        below, _ = _categorize("tool_call", {"phase": "completed", "name": "bash",
                                             "isError": True, "durationMs": 119_999})
        assert at == "tool_error:bash:timeout"
        assert below == "tool_error:bash:slow"

    def test_slow(self):
        from analyzer import _categorize
        cat, _ = _categorize("tool_call", {
            "phase": "completed", "name": "bash", "isError": True,
            "truncated": False, "durationMs": 30_000,
        })
        assert cat == "tool_error:bash:slow"

    def test_slow_lower_boundary(self):
        """>=30000 ⇒ slow; 29999 ⇒ plain."""
        from analyzer import _categorize
        at, _ = _categorize("tool_call", {"phase": "completed", "name": "bash",
                                          "isError": True, "durationMs": 30_000})
        below, _ = _categorize("tool_call", {"phase": "completed", "name": "bash",
                                             "isError": True, "durationMs": 29_999})
        assert at == "tool_error:bash:slow"
        assert below == "tool_error:bash:plain"

    def test_plain_fast(self):
        from analyzer import _categorize
        cat, _ = _categorize("tool_call", {
            "phase": "completed", "name": "bash", "isError": True,
            "truncated": False, "durationMs": 500,
        })
        assert cat == "tool_error:bash:plain"

    def test_plain_when_duration_missing(self):
        """No durationMs field ⇒ treated as 0 ⇒ plain (never crashes)."""
        from analyzer import _categorize
        cat, _ = _categorize("tool_call", {
            "phase": "completed", "name": "bash", "isError": True,
        })
        assert cat == "tool_error:bash:plain"

    def test_subclass_applies_to_any_tool(self):
        """Subclassing keys off the tool name, not just bash."""
        from analyzer import _categorize
        cat, _ = _categorize("tool_call", {
            "phase": "completed", "name": "read_file", "isError": True,
            "durationMs": 200_000,
        })
        assert cat == "tool_error:read_file:timeout"


class TestSubclassIngestion:
    """End-to-end: subclasses survive load_witness_friction + per-session cap + filter."""

    def test_slow_subclass_capped(self, tmp_path):
        """7 slow bash errors ⇒ tool_error:bash:slow capped at PER_SESSION_CAP, no :plain."""
        make_trace(tmp_path, "sess_slow",
                   [error_event_ex(i, duration_ms=60_000) for i in range(7)])
        os.environ["AFK_WITNESS_DIR"] = str(tmp_path)
        import importlib
        import analyzer as mod
        importlib.reload(mod)
        results = mod.load_witness_friction()
        os.environ.pop("AFK_WITNESS_DIR", None)
        importlib.reload(mod)

        fc = results[0]["friction_counts"]
        assert fc.get("tool_error:bash:slow") == 5
        assert "tool_error:bash:plain" not in fc

    def test_distinct_subclasses_split(self, tmp_path):
        """One error of each class in a session ⇒ four distinct keys, count 1 each."""
        events = [
            error_event_ex(0, truncated=True),
            error_event_ex(1, duration_ms=150_000),
            error_event_ex(2, duration_ms=60_000),
            error_event_ex(3, duration_ms=500),
        ]
        make_trace(tmp_path, "sess_mix", events)
        os.environ["AFK_WITNESS_DIR"] = str(tmp_path)
        import importlib
        import analyzer as mod
        importlib.reload(mod)
        results = mod.load_witness_friction()
        os.environ.pop("AFK_WITNESS_DIR", None)
        importlib.reload(mod)

        fc = results[0]["friction_counts"]
        assert fc.get("tool_error:bash:truncated") == 1
        assert fc.get("tool_error:bash:timeout") == 1
        assert fc.get("tool_error:bash:slow") == 1
        assert fc.get("tool_error:bash:plain") == 1

    def test_category_filter_prefix_matches_subclasses(self, tmp_path):
        """--category tool_error:bash still selects subclassed witness sessions (req 1)."""
        make_trace(tmp_path, "s_slow", [error_event_ex(0, duration_ms=60_000)])
        make_trace(tmp_path, "s_sub", [subagent_fail_event()])
        os.environ["AFK_WITNESS_DIR"] = str(tmp_path)
        import importlib
        import analyzer as mod
        importlib.reload(mod)
        results = mod.load_witness_friction(category="tool_error:bash")
        os.environ.pop("AFK_WITNESS_DIR", None)
        importlib.reload(mod)

        assert len(results) == 1
        assert results[0]["session_id"] == "s_slow"

    def test_category_filter_exact_subclass(self, tmp_path):
        """--category tool_error:bash:slow selects only the matching subclass."""
        make_trace(tmp_path, "s_slow", [error_event_ex(0, duration_ms=60_000)])
        make_trace(tmp_path, "s_plain", [error_event_ex(0, duration_ms=500)])
        os.environ["AFK_WITNESS_DIR"] = str(tmp_path)
        import importlib
        import analyzer as mod
        importlib.reload(mod)
        results = mod.load_witness_friction(category="tool_error:bash:slow")
        os.environ.pop("AFK_WITNESS_DIR", None)
        importlib.reload(mod)

        assert len(results) == 1
        assert results[0]["session_id"] == "s_slow"


# ---------------------------------------------------------------------------
# forge ranking: high-confidence failure classes outrank :plain
# ---------------------------------------------------------------------------

class TestForgeRanking:
    def _session(self, sid: str, counts: dict) -> dict:
        return {"session_id": sid, "outcome": "completed", "goal": "",
                "friction_detail": "d", "friction_counts": counts}

    def test_priority_weights(self):
        from analyzer import _friction_priority
        assert _friction_priority("tool_error:bash:timeout") == 3
        assert _friction_priority("tool_error:bash:truncated") == 3
        assert _friction_priority("tool_error:bash:slow") == 2
        assert _friction_priority("tool_error:bash:plain") == 0
        # non-subclassed / non-tool-error categories are normal (above plain)
        assert _friction_priority("closure:abort") == 1
        assert _friction_priority("tool_error:bash") == 1          # facet-origin, no subclass
        assert _friction_priority("subagent_fail:TypeError") == 1

    def test_high_confidence_ranked_above_plain_despite_higher_plain_count(self):
        from analyzer import summarize
        out = summarize([
            self._session("a", {"tool_error:bash:plain": 50}),    # biggest by count
            self._session("b", {"tool_error:bash:timeout": 3}),
            self._session("c", {"tool_error:bash:slow": 2}),
        ])
        order = [c["category"] for c in out["friction_categories"]]
        assert order.index("tool_error:bash:timeout") < order.index("tool_error:bash:plain")
        assert order.index("tool_error:bash:slow") < order.index("tool_error:bash:plain")
        assert order[-1] == "tool_error:bash:plain"               # plain sinks to the bottom

    def test_within_tier_count_order_preserved(self):
        from analyzer import summarize
        out = summarize([
            self._session("a", {"tool_error:bash:timeout": 2}),
            self._session("b", {"tool_error:read_file:timeout": 9}),
        ])
        order = [c["category"] for c in out["friction_categories"]]
        # same confidence tier ⇒ higher count ranks first
        assert order.index("tool_error:read_file:timeout") < order.index("tool_error:bash:timeout")

    def test_normal_categories_rank_above_plain(self):
        from analyzer import summarize
        out = summarize([
            self._session("a", {"tool_error:bash:plain": 99}),
            self._session("b", {"closure:abort": 1}),
        ])
        order = [c["category"] for c in out["friction_categories"]]
        assert order.index("closure:abort") < order.index("tool_error:bash:plain")
