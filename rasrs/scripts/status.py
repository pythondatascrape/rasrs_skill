#!/usr/bin/env python3
"""Summarize the request lines `rasrs serve` writes to stderr (contracts/v2/telemetry.json):
counts and p50/p95 duration per operation and outcome, degraded calls, FTS rebuilds, and recalls
that found nothing (candidates_after_dedupe 0) grouped by caller (mcp_request_id, which a client
sets by naming its JSON-RPC id, e.g. "plan-recall"; unnamed callers show as "-").

Lines that are not JSON objects are skipped, and a prefix before the first "{" (a timestamp
added by a log collector) is ignored. Lines carry ids, counts and timings only, never content.
"""
from __future__ import annotations

import argparse
import json
import math
import sys
from collections import Counter, defaultdict
from pathlib import Path

DEFAULT_LOG = Path("~/Library/Logs/rasrs.log").expanduser()


def events(lines):
    for line in lines:
        i = line.find("{")
        if i < 0:
            continue
        try:
            ev = json.loads(line[i:])
        except ValueError:
            continue
        if isinstance(ev, dict) and "event" in ev:
            yield ev


def pct(xs: list[int], p: float) -> int:
    xs = sorted(xs)
    return xs[min(len(xs) - 1, max(0, math.ceil(p * len(xs)) - 1))] if xs else 0


def summarize(evs) -> str:
    by = defaultdict(list)
    degraded, rebuilds, empty, empty_total = Counter(), [], Counter(), Counter()
    for ev in evs:
        if ev["event"] == "rebuild_finished":
            rebuilds.append(ev)
        if ev["event"] != "request":
            continue
        op, out = ev.get("operation", "?"), ev.get("outcome", "?")
        by[(op, out)].append(int(ev.get("duration_ms") or 0))
        degraded[op] += bool(ev.get("degraded"))
        if op == "recall" and out == "ok":
            caller = ev.get("mcp_request_id") or "-"
            empty_total[caller] += 1
            empty[caller] += ev.get("candidates_after_dedupe") == 0
    if not by and not rebuilds:
        return "no request lines"
    out = ["operation  outcome          calls    p50ms    p95ms"]
    for (op, oc), ds in sorted(by.items()):
        out.append(f"{op:10} {oc:15} {len(ds):6} {pct(ds, .5):8} {pct(ds, .95):8}")
    if any(degraded.values()):
        out.append("degraded: " + ", ".join(f"{op} {n}" for op, n in sorted(degraded.items()) if n))
    if rebuilds:
        last = rebuilds[-1]
        out.append(f"fts rebuilds: {len(rebuilds)}, last {last.get('outcome')} "
                   f"({last.get('atoms')} atoms, {last.get('duration_ms')} ms)")
    if empty_total:
        out.append("empty recalls by caller (empty/ok recalls):")
        for caller, n in sorted(empty_total.items(), key=lambda kv: (-empty[kv[0]], kv[0])):
            out.append(f"  {caller:32} {empty[caller]}/{n}")
    return "\n".join(out)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("log", nargs="?", default=str(DEFAULT_LOG), help=f"log file, or - for stdin (default {DEFAULT_LOG})")
    a = ap.parse_args()
    try:
        if a.log == "-":
            print(summarize(events(sys.stdin)))
        else:
            with open(a.log, encoding="utf-8", errors="replace") as f:
                print(summarize(events(f)))
    except OSError as e:
        print(f"cannot read log: {e}")
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
