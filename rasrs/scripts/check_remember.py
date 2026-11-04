#!/usr/bin/env python3
"""Check a RASRS remember request before sending it: the claim rules, text and per-Atom limits,
tag pattern, evidence requirements and link relations the server enforces.

Reads one request (JSON object, the remember tool's arguments) from a file or stdin (`-`).
Exit 0 when it would pass validation, 1 listing each problem, 2 when the input is not JSON.
Limits default to the server's policy defaults (contracts/v2/policy-defaults.json); pass the
operator's values when they were raised.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
import unicodedata

TAG = re.compile(r"^[a-z0-9._:/-]{1,64}$")
LIST_MARKER = re.compile(r"(?:^|\s)(?:\(\d{1,3}\)|\d{1,3}\)|\d{1,3}\.\s)")
RELATIONS = {"depends-on", "supersedes", "references", "relates-to"}
EVIDENCE = {"source", "test", "design_record", "commit", "issue", "manual"}
BIDI = set("‪‫‬‭‮⁦⁧⁨⁩")
DEFAULTS = {"claim": 500, "rationale": 2000, "tags": 20, "files": 20, "symbols": 20,
            "evidence": 10, "links": 20}


def sentences(s: str) -> int:
    """A sentence ends at a run of . ! ? followed by whitespace or the end, so atom.go ends none."""
    n, content, i = 0, False, 0
    while i < len(s):
        ch = s[i]
        i += 1
        if ch not in ".!?":
            content = content or not ch.isspace()
            continue
        while i < len(s) and s[i] in ".!?":
            i += 1
        if i == len(s) or s[i].isspace():
            n += content
            content = False
    return n + content


def bad_text(s: str, multiline: bool) -> str:
    for ch in s:
        if ch in BIDI:
            return "contains a bidi control character"
        if multiline and ch in "\n\t":
            continue
        if unicodedata.category(ch) == "Cc":
            return "contains a control character"
    return ""


def check(req: dict, lim: dict) -> list[str]:
    p = []
    if not isinstance(req, dict):
        return ["request is not a JSON object"]
    if not str(req.get("project") or "").strip():
        p.append("project: missing")
    claim = req.get("claim")
    if not isinstance(claim, str) or not claim.strip():
        p.append("claim: missing or empty")
    else:
        if m := bad_text(claim, False):
            p.append(f"claim: {m}")
        if len(claim) > lim["claim"]:
            p.append(f"claim: {len(claim)} characters, max {lim['claim']}")
        if (n := sentences(claim)) > 2:
            p.append(f"claim: {n} sentences, max 2")
        if LIST_MARKER.search(claim):
            p.append("claim: contains an inline numbered list")
    rat = req.get("rationale")
    if not isinstance(rat, str) or not rat.strip():
        p.append("rationale: missing or empty")
    else:
        if m := bad_text(rat, True):
            p.append(f"rationale: {m}")
        if len(rat) > lim["rationale"]:
            p.append(f"rationale: {len(rat)} characters, max {lim['rationale']}")
    for key in ("tags", "files", "symbols", "links"):
        v = req.get(key, [])
        if not isinstance(v, list):
            p.append(f"{key}: not a list")
            continue
        if len(v) > lim[key]:
            p.append(f"{key}: {len(v)} items, max {lim[key]}")
        if key != "links" and len({json.dumps(x) for x in v}) != len(v):
            p.append(f"{key}: duplicate items")
    for t in req.get("tags", []) if isinstance(req.get("tags"), list) else []:
        if not isinstance(t, str) or not TAG.match(t):
            p.append(f"tags: {t!r} does not match {TAG.pattern}")
    for i, ln in enumerate(req.get("links", []) if isinstance(req.get("links"), list) else []):
        if not isinstance(ln, dict) or not ln.get("to"):
            p.append(f"links[{i}]: needs 'to'")
        elif ln.get("relation") not in RELATIONS:
            p.append(f"links[{i}]: relation {ln.get('relation')!r} not one of {', '.join(sorted(RELATIONS))}")
    ev = req.get("evidence")
    if not isinstance(ev, list) or not ev:
        p.append("evidence: at least one item is required")
        ev = []
    elif len(ev) > lim["evidence"]:
        p.append(f"evidence: {len(ev)} items, max {lim['evidence']}")
    for i, e in enumerate(ev):
        if not isinstance(e, dict):
            p.append(f"evidence[{i}]: not an object")
            continue
        t = e.get("type")
        has = lambda *ks: all(str(e.get(k) or "").strip() for k in ks)  # noqa: E731
        if t not in EVIDENCE:
            p.append(f"evidence[{i}]: type {t!r} not one of {', '.join(sorted(EVIDENCE))}")
        elif t in ("source", "test") and not has("path", "revision"):
            p.append(f"evidence[{i}]: {t} needs path and revision")
        elif t == "design_record" and not (has("path", "revision") or has("reference")):
            p.append(f"evidence[{i}]: design_record needs path and revision, or reference")
        elif t == "commit" and not has("revision"):
            p.append(f"evidence[{i}]: commit needs revision")
        elif t == "issue" and not has("reference"):
            p.append(f"evidence[{i}]: issue needs reference")
        ls, le = e.get("line_start"), e.get("line_end")
        for k, v in (("line_start", ls), ("line_end", le)):
            if v is not None and (not isinstance(v, int) or isinstance(v, bool) or v < 1):
                p.append(f"evidence[{i}]: {k} must be an integer >= 1")
        if isinstance(ls, int) and isinstance(le, int) and le < ls:
            p.append(f"evidence[{i}]: line_end before line_start")
    return p


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("request", help="JSON file with the remember arguments, or - for stdin")
    for k, v in DEFAULTS.items():
        ap.add_argument(f"--{k}-max", type=int, default=v, dest=k)
    a = ap.parse_args()
    try:
        raw = sys.stdin.read() if a.request == "-" else open(a.request, encoding="utf-8").read()
        req = json.loads(raw)
    except (OSError, ValueError) as e:
        print(f"cannot read request: {e}")
        return 2
    if isinstance(req, dict) and isinstance(req.get("arguments"), dict):
        req = req["arguments"]  # a whole {"name": "remember", "arguments": {...}} call
    problems = check(req, {k: getattr(a, k) for k in DEFAULTS})
    for x in problems:
        print(x)
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
