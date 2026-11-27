#!/usr/bin/env python3
import argparse
import fnmatch
import importlib.util
import json
import math
import os
import sys
from datetime import date, datetime
from pathlib import Path

HERE = Path(__file__).resolve().parent


def read_budget():
    spec = importlib.util.spec_from_file_location("read_budget", HERE / "read-budget.py")
    rb = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(rb)
    budget = json.loads(rb.BUDGET.read_text(encoding="utf-8"))
    return {name: m["total"] for name, m in rb.measure(budget).items()}


def nearest_rank(values, p):
    values = sorted(values)
    if not values:
        return None
    return values[max(0, math.ceil(p / 100 * len(values)) - 1)]


def median(values):
    values = sorted(values)
    if not values:
        return None
    mid = len(values) // 2
    return values[mid] if len(values) % 2 else (values[mid - 1] + values[mid]) / 2


def eval_summary(paths):
    """The eval JSON has no token counts. A case --max-cost-usd stopped before its first run is not in it at all,
    so `not_run` lists suite folders no file has.
    """
    files = [json.loads(Path(p).read_text(encoding="utf-8")) for p in paths]
    cases, runs_of, threshold_of, suite_names, thresholds = {}, {}, {}, None, []
    for data in files:
        suite = data.get("suite") or {}
        thresholds.append(suite.get("threshold"))
        for case in data.get("cases", []):
            runs = (case.get("arms") or {}).get("with") or []
            agg = case.get("aggregates") or {}
            runs_of[case["name"]] = runs
            threshold_of[case["name"]] = suite.get("threshold")
            cases[case["name"]] = {"pass": agg.get("passRate"), "score": agg.get("score"), "runs": len(runs),
                                   "errors": sum(1 for r in runs if r.get("error")),
                                   "complete": bool(runs) and len(runs) >= (case.get("runsPerCase") or len(runs))
                                   and not any(r.get("skippedPaidGraders") for r in runs)}
        root = suite.get("root")
        if root and (Path(root) / "evals").is_dir():
            pattern = suite.get("caseFilter") or "*"
            names = {d.name for d in (Path(root) / "evals").iterdir() if (d / "case.yaml").is_file() or (d / "prompt.md").is_file()}
            suite_names = (suite_names or set()) | {n for n in names if fnmatch.fnmatch(n, pattern)}
    threshold = thresholds[-1] if len(set(thresholds)) == 1 else None
    runs = [r for rs in runs_of.values() for r in rs]
    seconds = [r["durationSeconds"] for r in runs if r.get("durationSeconds") is not None]
    rates = [c["pass"] for c in cases.values() if c["pass"] is not None]
    incomplete = sorted(n for n, c in cases.items() if not c["complete"])
    not_run = sorted(suite_names - set(cases)) if suite_names is not None else None
    cases_left_out = bool(not_run or incomplete)
    speed = {"seconds_p50": median(seconds),
             "cost_p50": median([r["costUsd"] for r in runs if r.get("costUsd") is not None]),
             "turns_p50": median([r["turns"] for r in runs if r.get("turns") is not None])}

    def total(key):
        values = [d.get(key) for d in files if d.get(key) is not None]
        return sum(values) if values else None

    return {
        "cases": cases,
        "passed": sum(1 for n, c in cases.items() if c["score"] is not None and c["score"] >= (1 if threshold_of[n] is None else threshold_of[n])),
        "total": len(cases),
        "suite_total": len(suite_names | set(cases)) if suite_names is not None else None,
        "pass_rate": sum(rates) / len(rates) if rates else None,
        "incomplete": incomplete,
        "not_run": not_run,
        "all_runs_passed": sum(1 for c in cases.values() if c["complete"] and c["pass"] == 1),
        "threshold": threshold,
        # Without the suite folder, a capped earlier file can't say which of its cases a later file replaced: trust the last file.
        "partial": cases_left_out if suite_names is not None else bool(incomplete) or bool(files[-1].get("partial")),
        "files": len(files),
        "cost_usd": total("costUsd"),
        "seconds": total("durationSeconds"),
        "speed": speed if any(v is not None for v in speed.values()) else None,
        "tokens": None,
    }


def log_tokens(run_dir):
    """fresh (input + cache creation), cache_read, output, summed over every `result` event of the run's logs.

    Each result event carries the usage since the previous one (total_cost_usd is the only cumulative field),
    so a resumed or wrapped-up session adds events and they are summed. `usage` is the main session's only:
    subagents' tokens are in `modelUsage`, which this leaves out, while cost_usd covers both. None when no log has a result event.
    """
    total, seen = {"fresh": 0, "cache_read": 0, "output": 0}, False
    for log in sorted(Path(run_dir).glob("log*.jsonl")):
        for line in log.read_text(encoding="utf-8", errors="replace").splitlines():
            if '"type":"result"' not in line and '"type": "result"' not in line:
                continue
            try:
                event = json.loads(line)
            except ValueError:
                continue
            usage = event.get("usage") if event.get("type") == "result" else None
            if not usage:
                continue
            seen = True
            total["fresh"] += (usage.get("input_tokens") or 0) + (usage.get("cache_creation_input_tokens") or 0)
            total["cache_read"] += usage.get("cache_read_input_tokens") or 0
            total["output"] += usage.get("output_tokens") or 0
    return total if seen else None


def minutes(result):
    try:
        start = datetime.strptime(result["started_at"], "%Y-%m-%dT%H:%M:%S%z")
        end = datetime.strptime(result["finished_at"], "%Y-%m-%dT%H:%M:%S%z")
    except (KeyError, TypeError, ValueError):
        return None
    return (end - start).total_seconds() / 60


def session_sum(result, field):
    sessions = result.get("sessions")
    values = [s.get(field) for s in sessions.values() if isinstance(s, dict)] if isinstance(sessions, dict) else []
    values = [v for v in values if v is not None]
    return sum(values) if values else None


def trend(runs_dir):
    by_slot = {}
    for path in sorted(Path(runs_dir).glob("*/result.json")):
        try:
            result = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            continue
        if not isinstance(result, dict):
            continue
        by_slot.setdefault(result.get("slot") or "?", []).append((path.parent, result))
    out = {}
    for slot, runs in sorted(by_slot.items()):
        done = [(d, r) for d, r in runs if r.get("status") == "done"]
        mins = [m for m in (minutes(r) for _, r in done) if m is not None]
        turns = [t for t in (session_sum(r, "turns") for _, r in done) if t is not None]
        costs = [c for c in (session_sum(r, "cost_usd") for _, r in done) if c is not None]
        tokens = [t for t in (log_tokens(d) for d, _ in done) if t is not None]
        out[slot] = {
            "n": len(runs),
            "failed": sum(1 for _, r in runs if r.get("status") == "failed"),
            "done": len(done),
            "minutes_p50": median(mins), "minutes_p90": nearest_rank(mins, 90),
            "turns_p50": median(turns),
            "cost_p50": median(costs), "cost_p90": nearest_rank(costs, 90),
            "tokens_p50": {k: median([t[k] for t in tokens]) for k in ("fresh", "cache_read", "output")} if tokens else None,
            "gaps_rate": sum(1 for _, r in done if r.get("gaps")) / len(done) if done else None,
            "unverified_rate": sum(1 for _, r in done if r.get("unverified")) / len(done) if done else None,
        }
    return out


def runs_dir_exists(runs_dir):
    if Path(runs_dir).is_dir():
        return True
    print(f"baseline: --runs {runs_dir} is not a directory; trend is empty", file=sys.stderr)
    return False


def build(version, eval_path, runs_dir):
    return {
        "version": version,
        "date": date.today().isoformat(),
        "eval": eval_summary(eval_path) if eval_path else None,
        "read_budget": read_budget(),
        "trend": trend(runs_dir) if runs_dir and runs_dir_exists(runs_dir) else {},
    }


def flatten(obj, prefix=""):
    out = {}
    if isinstance(obj, dict):
        for k, v in obj.items():
            out.update(flatten(v, f"{prefix}{k}."))
    elif isinstance(obj, (int, float)) and not isinstance(obj, bool):
        out[prefix[:-1]] = obj
    elif obj is None and prefix:
        out[prefix[:-1]] = None
    return out


def diff(old, new):
    a, b = (flatten({k: d.get(k) for k in ("eval", "read_budget", "trend")}) for d in (old, new))
    rows = []
    for key in sorted(set(a) | set(b)):
        x, y = a.get(key), b.get(key)
        if x is None and y is None:
            continue
        change = y - x if x is not None and y is not None else None
        rate = change / x * 100 if change is not None and x else (0.0 if change == 0 else None)
        rows.append((key, x, y, change, rate))
    return rows


def fmt(v):
    if v is None:
        return "—"
    if isinstance(v, float) and not v.is_integer():
        return f"{v:,.3f}".rstrip("0").rstrip(".")
    return f"{int(v):,}"


def print_diff(old, new):
    print(f"| metric | {old.get('version')} ({old.get('date')}) | {new.get('version')} ({new.get('date')}) | change | % |")
    print("|---|---|---|---|---|")
    for key, x, y, change, rate in diff(old, new):
        sign = "+" if change and change > 0 else ""
        pct_txt = "—" if rate is None else f"{'+' if rate > 0 else ''}{rate:.1f}%"
        print(f"| {key} | {fmt(x)} | {fmt(y)} | {sign}{fmt(change)} | {pct_txt} |")
    for side in (old, new):
        e = side.get("eval") or {}
        if e.get("partial") or e.get("not_run") or e.get("incomplete"):
            print(f"warning: {side.get('version')} eval is partial (not_run {len(e.get('not_run') or [])}, "
                  f"incomplete {len(e.get('incomplete') or [])}); its eval numbers don't cover the suite")


def main(argv=None):
    argv = sys.argv[1:] if argv is None else argv
    if argv and argv[0] == "diff":
        p = argparse.ArgumentParser(prog="baseline.py diff")
        p.add_argument("old")
        p.add_argument("new")
        args = p.parse_args(argv[1:])
        print_diff(*(json.loads(Path(f).read_text(encoding="utf-8")) for f in (args.old, args.new)))
        return 0
    p = argparse.ArgumentParser(prog="baseline.py")
    p.add_argument("--version", required=True)
    p.add_argument("--eval", dest="eval_path", action="append",
                   help="an eval --json file; repeat it to merge a rerun of the cases a cost cap left out (later wins)")
    gbase_home = Path(os.environ.get("GBASE_HOME") or "~/.gbase").expanduser()
    p.add_argument("--runs", default=str(gbase_home / "runs"))
    p.add_argument("--out")
    args = p.parse_args(argv)
    tree = json.loads((HERE.parent / "plugins/base/.claude-plugin/plugin.json").read_text(encoding="utf-8"))["version"]
    if tree != args.version:
        print(f"baseline: --version {args.version}, but this tree is gbase {tree}; read_budget measures this tree", file=sys.stderr)
    text = json.dumps(build(args.version, args.eval_path, args.runs), ensure_ascii=False, indent=2) + "\n"
    if args.out:
        Path(args.out).write_text(text, encoding="utf-8")
        print(f"baseline: {args.out}")
    else:
        sys.stdout.write(text)
    return 0


if __name__ == "__main__":
    sys.exit(main())
