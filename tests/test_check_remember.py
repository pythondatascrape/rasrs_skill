import json

from conftest import run

GOOD = {"project": "orders",
        "claim": "Orders are retried at most three times before moving to the dead-letter queue.",
        "rationale": "Unbounded retries amplified a payment-provider outage.\nSee the incident.",
        "evidence": [{"type": "source", "path": "internal/orders/retry.go",
                      "revision": "0123456789abcdef0123456789abcdef01234567", "line_start": 10, "line_end": 24}],
        "files": ["internal/orders/retry.go"], "tags": ["orders", "decision"]}


def chk(tmp_path, req, *args):
    p = tmp_path / "req.json"
    p.write_text(json.dumps(req))
    return run("check_remember.py", str(p), *args, cwd=tmp_path)


def test_a_valid_request_passes_also_wrapped_as_a_tool_call(tmp_path):
    assert chk(tmp_path, GOOD).returncode == 0
    r = run("check_remember.py", "-", cwd=tmp_path, stdin=json.dumps({"name": "remember", "arguments": GOOD}))
    assert r.returncode == 0, r.stdout


def test_claim_rules(tmp_path):
    three = GOOD | {"claim": "One. Two. Three."}
    listed = GOOD | {"claim": "Retries: 1) once 2) twice"}
    long = GOOD | {"claim": "x" * 501}
    for req, want in ((three, "3 sentences"), (listed, "numbered list"), (long, "501 characters")):
        r = chk(tmp_path, req)
        assert r.returncode == 1 and want in r.stdout, r.stdout
    assert chk(tmp_path, GOOD | {"claim": "atom.go in v1.2 holds it. Really."}).returncode == 0
    assert chk(tmp_path, long, "--claim-max", "1000").returncode == 0


def test_evidence_requirements(tmp_path):
    cases = [([], "at least one"),
             ([{"type": "source", "path": "a.go"}], "source needs path and revision"),
             ([{"type": "design_record", "path": "d.md"}], "design_record needs"),
             ([{"type": "commit"}], "commit needs revision"),
             ([{"type": "issue"}], "issue needs reference"),
             ([{"type": "guess"}], "type 'guess'"),
             ([{"type": "manual", "line_start": 5, "line_end": 2}], "line_end before")]
    for ev, want in cases:
        r = chk(tmp_path, GOOD | {"evidence": ev})
        assert r.returncode == 1 and want in r.stdout, (ev, r.stdout)
    for ev in ([{"type": "manual"}], [{"type": "design_record", "reference": "D-01"}]):
        assert chk(tmp_path, GOOD | {"evidence": ev}).returncode == 0


def test_tags_links_and_counts(tmp_path):
    r = chk(tmp_path, GOOD | {"tags": ["Bad Tag"], "links": [{"to": "x", "relation": "replaces"}],
                              "files": [f"f{i}" for i in range(21)]})
    assert r.returncode == 1
    assert "'Bad Tag'" in r.stdout and "relation 'replaces'" in r.stdout and "21 items, max 20" in r.stdout


def test_missing_project_and_control_characters(tmp_path):
    r = chk(tmp_path, {k: v for k, v in GOOD.items() if k != "project"} | {"claim": "a\u202eb"})
    assert "project: missing" in r.stdout and "bidi" in r.stdout


def test_unreadable_input_exits_2(tmp_path):
    assert run("check_remember.py", "-", cwd=tmp_path, stdin="{").returncode == 2
