import json

from conftest import run


def line(op, outcome="ok", ms=10, after=1, rid=None, degraded=False):
    ev = {"event": "request", "correlation_id": "c", "operation": op, "outcome": outcome,
          "duration_ms": ms, "stages": {}, "candidates_before_dedupe": after,
          "candidates_after_dedupe": after, "graph_nodes": 0, "graph_edges": 0, "graph_depth": 0,
          "degraded": degraded}
    if rid:
        ev["mcp_request_id"] = rid
    return json.dumps(ev)


def test_summary_groups_empty_recalls_by_caller(tmp_path):
    log = "\n".join([
        "2026-11-04T10:00:00Z " + line("recall", ms=10, after=0, rid="plan-recall"),
        line("recall", ms=30, after=0, rid="plan-recall"),
        line("recall", ms=50, after=2, rid="plan-recall"),
        line("recall", ms=20, after=0),
        line("remember", ms=7, degraded=True),
        line("remember", outcome="error", ms=3),
        "not json",
        json.dumps({"event": "rebuild_finished", "duration_ms": 12, "atoms": 40, "outcome": "ok"}),
    ])
    (tmp_path / "rasrs.log").write_text(log)
    r = run("status.py", "rasrs.log", cwd=tmp_path)
    assert r.returncode == 0, r.stderr
    out = r.stdout
    assert ["recall", "ok", "4", "20", "50"] in [x.split() for x in out.splitlines()]
    assert "remember   error" in out and "degraded: remember 1" in out
    assert "fts rebuilds: 1, last ok (40 atoms, 12 ms)" in out
    assert out.index("plan-recall") < out.index("  - ")
    assert "plan-recall                      2/3" in out and "1/1" in out


def test_empty_log_and_missing_file(tmp_path):
    assert run("status.py", "-", cwd=tmp_path, stdin="").stdout.strip() == "no request lines"
    assert run("status.py", "nope.log", cwd=tmp_path).returncode == 2
