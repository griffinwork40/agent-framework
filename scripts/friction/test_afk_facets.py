"""Tests for the agent-afk facet source (afk_facets.py) and its wiring into analyzer.py."""
import json
import os
import subprocess
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import afk_facets  # noqa: E402
import analyzer  # noqa: E402

HERE = Path(__file__).parent


def iso(days_ago: float = 0) -> str:
    return (datetime.now(timezone.utc) - timedelta(days=days_ago)).strftime("%Y-%m-%dT%H:%M:%S.000Z")


def write_facet(root: Path, session_id: str, **fields) -> None:
    root.mkdir(parents=True, exist_ok=True)
    facet = {
        "derived_from": "afk-session",
        "session_id": session_id,
        "start_time": iso(1),
        "underlying_goal": f"goal for {session_id}",
        "outcome": "fully_achieved",
        "session_type": "implementation",
        "brief_summary": "summary",
        "friction_counts": {},
        "friction_detail": "",
    }
    facet.update(fields)
    (root / f"{session_id}.json").write_text(json.dumps(facet))


class TestResolveDir:
    def test_facets_override_wins(self, monkeypatch, tmp_path):
        monkeypatch.setenv("AFK_FACETS_DIR", str(tmp_path / "x"))
        monkeypatch.setenv("AFK_FRAMEWORK_DIR", str(tmp_path / "fw"))
        assert afk_facets.resolve_afk_facets_dir() == tmp_path / "x"

    def test_framework_dir(self, monkeypatch, tmp_path):
        monkeypatch.delenv("AFK_FACETS_DIR", raising=False)
        monkeypatch.setenv("AFK_FRAMEWORK_DIR", str(tmp_path / "fw"))
        assert afk_facets.resolve_afk_facets_dir() == tmp_path / "fw" / "facets"

    def test_afk_home(self, monkeypatch, tmp_path):
        monkeypatch.delenv("AFK_FACETS_DIR", raising=False)
        monkeypatch.delenv("AFK_FRAMEWORK_DIR", raising=False)
        monkeypatch.setenv("AFK_HOME", str(tmp_path))
        assert afk_facets.resolve_afk_facets_dir() == tmp_path / "agent-framework" / "facets"


class TestLoadAfkFacets:
    def test_maps_tool_counts_to_unclassified_and_caps(self, tmp_path):
        write_facet(tmp_path, "s1", friction_counts={"bash": 9, "read_file": 1})
        rec = afk_facets.load_afk_facets(days=28, cap=5, facets_dir=tmp_path)["s1"]
        assert rec["friction_counts"] == {
            "tool_error:bash:unclassified": 5,
            "tool_error:read_file:unclassified": 1,
        }
        assert rec["goal"] == "goal for s1"
        assert rec["meta"]["start_time"]

    def test_window_excludes_old(self, tmp_path):
        write_facet(tmp_path, "old", start_time=iso(40), friction_counts={"bash": 1})
        write_facet(tmp_path, "new", start_time=iso(2), friction_counts={"bash": 1})
        assert set(afk_facets.load_afk_facets(days=28, cap=5, facets_dir=tmp_path)) == {"new"}

    def test_keeps_frictionless_facets_for_goal_enrichment(self, tmp_path):
        write_facet(tmp_path, "clean")
        assert afk_facets.load_afk_facets(28, 5, tmp_path)["clean"]["friction_counts"] == {}

    def test_skips_malformed_and_foreign(self, tmp_path):
        tmp_path.mkdir(exist_ok=True)
        (tmp_path / "bad.json").write_text("{not json")
        write_facet(tmp_path, "cc", derived_from="claude-code", friction_counts={"bash": 1})
        assert afk_facets.load_afk_facets(28, 5, tmp_path) == {}

    def test_missing_dir(self, tmp_path):
        assert afk_facets.load_afk_facets(28, 5, tmp_path / "nope") == {}


class TestEnrich:
    def witness(self, sid="s1", outcome="completed"):
        return {
            "session_id": sid, "goal": "", "outcome": outcome, "summary": "",
            "session_type": "trace", "friction_counts": {"tool_error:bash:timeout": 1},
            "friction_detail": "tool_error:bash:timeout x1", "meta": {"start_time": iso(1)},
        }

    def afk(self, tmp_path, **fields):
        write_facet(tmp_path, "s1", **fields)
        return afk_facets.load_afk_facets(28, 5, tmp_path)

    def test_witness_session_gains_goal_but_not_counts(self, tmp_path):
        out = afk_facets.enrich_with_afk_facets([self.witness()], self.afk(tmp_path, friction_counts={"bash": 3}))
        assert len(out) == 1
        assert out[0]["goal"] == "goal for s1"
        assert out[0]["friction_counts"] == {"tool_error:bash:timeout": 1}
        assert out[0]["outcome"] == "fully_achieved"

    def test_witness_abort_is_preserved(self, tmp_path):
        out = afk_facets.enrich_with_afk_facets([self.witness(outcome="aborted")], self.afk(tmp_path))
        assert out[0]["outcome"] == "aborted"

    def test_facet_only_session_added_when_it_has_friction(self, tmp_path):
        out = afk_facets.enrich_with_afk_facets([], self.afk(tmp_path, friction_counts={"bash": 2}))
        assert [s["session_id"] for s in out] == ["s1"]

    def test_facet_only_session_without_friction_not_added(self, tmp_path):
        assert afk_facets.enrich_with_afk_facets([], self.afk(tmp_path)) == []

    def test_category_filter_matches_prefix(self, tmp_path):
        afk = self.afk(tmp_path, friction_counts={"bash": 2})
        assert afk_facets.enrich_with_afk_facets([], afk, category="tool_error:bash")
        assert not afk_facets.enrich_with_afk_facets([], afk, category="tool_error:grep")


def test_unclassified_ranks_with_plain():
    assert analyzer._friction_priority("tool_error:bash:unclassified") == 0
    assert analyzer._friction_priority("tool_error:bash:timeout") > 0


def test_cli_end_to_end_reads_afk_facets(tmp_path):
    facets = tmp_path / "facets"
    write_facet(facets, "s1", friction_counts={"bash": 2}, underlying_goal="ship the thing")
    env = {
        **os.environ,
        "AFK_FACETS_DIR": str(facets),
        "AFK_WITNESS_DIR": str(tmp_path / "no-witness"),
        "USAGE_DATA_DIR": str(tmp_path / "no-usage"),
    }
    out = subprocess.run(
        [sys.executable, str(HERE / "analyzer.py")], env=env, capture_output=True, text=True, check=True,
    )
    data = json.loads(out.stdout)
    assert data["total_sessions_with_friction"] == 1
    cat = data["friction_categories"][0]
    assert cat["category"] == "tool_error:bash:unclassified"
    assert cat["recent_examples"][0]["goal"] == "ship the thing"


class TestTraceLabelJoin:
    def ledger(self, sessions_dir: Path, sid: str, label: str) -> None:
        d = sessions_dir / sid
        d.mkdir(parents=True)
        (d / "events.jsonl").write_text(json.dumps({"kind": "meta", "sessionId": sid, "traceLabel": label}) + "\n")

    def test_trace_label_read_from_ledger(self, tmp_path):
        self.ledger(tmp_path, "sid", "lbl")
        assert afk_facets.trace_label_for("sid", tmp_path) == "lbl"
        assert afk_facets.trace_label_for("missing", tmp_path) is None

    def test_witness_session_joined_via_trace_label_and_rekeyed(self, tmp_path):
        facets, ledgers = tmp_path / "facets", tmp_path / "sessions"
        write_facet(facets, "sid", friction_counts={"bash": 3}, underlying_goal="real goal")
        self.ledger(ledgers, "sid", "lbl")
        witness = {
            "session_id": "lbl", "goal": "", "outcome": "completed", "summary": "",
            "session_type": "trace", "friction_counts": {"tool_error:bash:timeout": 1},
            "friction_detail": "x", "meta": {"start_time": iso(1)},
        }
        afk = afk_facets.load_afk_facets(28, 5, facets, ledgers)
        out = afk_facets.enrich_with_afk_facets([witness], afk)
        assert len(out) == 1
        assert out[0]["session_id"] == "sid"
        assert out[0]["goal"] == "real goal"
        assert out[0]["friction_counts"] == {"tool_error:bash:timeout": 1}
        assert "trace_label" not in out[0]
