import json

from conftest import git, run


def recall(*evidence):
    return {"project_id": "p", "results": [{"id": "a1", "evidence": list(evidence)}],
            "related": [], "related_status": "expanded", "degraded": [], "truncation": {}}


def fresh(repo, doc):
    return run("freshness.py", "--recall", "-", "--repo", str(repo.path), cwd=repo.path, stdin=json.dumps(doc))


def test_unchanged_evidence_is_fresh_and_commit_is_known(repo):
    r = fresh(repo, recall({"type": "source", "path": "retry.go", "revision": repo.first},
                           {"type": "commit", "revision": repo.first}))
    assert r.returncode == 0, r.stdout
    assert r.stdout.startswith("fresh") and "known" in r.stdout


def test_moved_changed_missing_and_unknown(repo):
    (repo.path / "retry.go").write_text("package orders\n\n// note\n\nconst max = 3\n\nfunc retry() {}\n")
    (repo.path / "gone.go").unlink()
    (repo.path / "other.go").write_text("package other\n")
    git(repo.path, "commit", "-qam", "edit")
    r = fresh(repo, {"structuredContent": recall(
        {"type": "source", "path": "retry.go", "revision": repo.first, "line_start": 3, "line_end": 3},
        {"type": "test", "path": "gone.go", "revision": repo.first},
        {"type": "source", "path": "other.go", "revision": repo.first},
        {"type": "commit", "revision": "f" * 40},
        {"type": "manual"})})
    assert r.returncode == 1
    lines = r.stdout.splitlines()
    assert lines[0].startswith("moved") and "now at line 5" in lines[0]
    assert [x.split()[0] for x in lines] == ["moved", "missing", "changed", "unknown"]


def test_needs_a_git_checkout(tmp_path):
    r = run("freshness.py", "--repo", str(tmp_path), cwd=tmp_path, stdin=json.dumps(recall()))
    assert r.returncode == 2
