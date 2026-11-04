"""Fixtures for this skill's tests: a throwaway git checkout with two commits."""
import subprocess
import sys
from types import SimpleNamespace
from pathlib import Path

import pytest

SKILL = Path(__file__).resolve().parent / "rasrs"


def run(script: str, *args, cwd: Path, stdin: str | None = None) -> subprocess.CompletedProcess:
    return subprocess.run([sys.executable, str(SKILL / "scripts" / script), *args],
                          cwd=cwd, capture_output=True, text=True, input=stdin)


def git(root: Path, *args: str) -> str:
    return subprocess.run(["git", "-c", "user.email=t@t", "-c", "user.name=t", *args], cwd=root,
                          check=True, capture_output=True, text=True).stdout.strip()


@pytest.fixture
def repo(tmp_path):
    """A git checkout (repo.path) whose first commit (repo.first) has retry.go, gone.go and other.go."""
    root = tmp_path / "proj"
    root.mkdir()
    git(root, "init", "-q")
    (root / "retry.go").write_text("package orders\n\nconst max = 3\n\nfunc retry() {}\n")
    (root / "gone.go").write_text("package orders\n")
    (root / "other.go").write_text("package orders\n")
    git(root, "add", "-A")
    git(root, "commit", "-qm", "init")
    return SimpleNamespace(path=root, first=git(root, "rev-parse", "HEAD"))
