#!/usr/bin/env python3
"""Check whether the evidence of recalled RASRS Atoms still matches a checkout. RASRS stores each
evidence revision as written and never checks it, so a top-ranked Atom can be stale.

Reads a recall result (the tool's structured result, or a whole MCP result holding
structuredContent) from a file or stdin (`-`). For every evidence item with a path and revision
it compares the file at that revision with the working tree of --repo:

  fresh     the file (or the cited lines) is unchanged
  moved     the cited lines are unchanged but now start at another line (shown)
  changed   the file, or the cited lines, differ
  missing   the file is gone from the working tree
  unknown   the revision is not a commit in this repository (fetch it, or it is not git)
  known     commit evidence whose revision exists here (nothing more to compare)

Exit 0 when nothing is changed, missing or unknown; 1 otherwise; 2 when the input is unusable.
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

BAD = {"changed", "missing", "unknown"}


def git(repo: Path, *args: str) -> subprocess.CompletedProcess:
    return subprocess.run(["git", "-C", str(repo), *args], capture_output=True)


def atoms(doc: dict) -> list[dict]:
    if isinstance(doc.get("structuredContent"), dict):
        doc = doc["structuredContent"]
    if isinstance(doc.get("result"), dict):  # a JSON-RPC reply
        return atoms(doc["result"])
    return [a for k in ("results", "related") for a in doc.get(k) or [] if isinstance(a, dict)]


def find(block: list[bytes], lines: list[bytes]) -> int:
    """1-based start of block in lines, or 0."""
    n = len(block)
    for i in range(len(lines) - n + 1):
        if lines[i:i + n] == block:
            return i + 1
    return 0


def judge(repo: Path, e: dict) -> tuple[str, str]:
    rev, path = str(e.get("revision") or ""), str(e.get("path") or "")
    if not rev:
        return "", ""
    if git(repo, "cat-file", "-e", f"{rev}^{{commit}}").returncode != 0:
        return "unknown", ""
    if not path:
        return "known", ""
    old = git(repo, "show", f"{rev}:{path}")
    cur = repo / path
    if not cur.is_file():
        return "missing", ""
    if old.returncode != 0:
        return "unknown", f"{path} not in {rev[:12]}"
    new = cur.read_bytes()
    ls, le = e.get("line_start"), e.get("line_end") or e.get("line_start")
    if not isinstance(ls, int):
        return ("fresh" if old.stdout == new else "changed"), ""
    block = old.stdout.splitlines()[ls - 1:le]
    lines = new.splitlines()
    if lines[ls - 1:le] == block:
        return "fresh", ""
    at = find(block, lines) if block else 0
    return ("moved", f"now at line {at}") if at else ("changed", "")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--recall", default="-", help="recall result JSON file, or - for stdin")
    ap.add_argument("--repo", default=".", help="the checkout to compare with (default: .)")
    a = ap.parse_args()
    try:
        raw = sys.stdin.read() if a.recall == "-" else Path(a.recall).read_text(encoding="utf-8")
        doc = json.loads(raw)
    except (OSError, ValueError) as err:
        print(f"cannot read recall result: {err}")
        return 2
    repo = Path(a.repo)
    if not isinstance(doc, dict) or git(repo, "rev-parse", "--git-dir").returncode != 0:
        print("need a recall result object and a git checkout (--repo)")
        return 2
    worst = 0
    for atom in atoms(doc):
        for e in atom.get("evidence") or []:
            if not isinstance(e, dict):
                continue
            status, note = judge(repo, e)
            if not status:
                continue
            where = e.get("path") or e.get("type", "")
            if isinstance(e.get("line_start"), int):
                where += f":{e['line_start']}-{e.get('line_end') or e['line_start']}"
            rev = str(e.get("revision"))[:12]
            print(f"{status:8} {atom.get('id', '?')} {where} @{rev}" + (f" ({note})" if note else ""))
            worst |= status in BAD
    return worst


if __name__ == "__main__":
    sys.exit(main())
