#!/usr/bin/env python3
"""Watch the skill repos gbase compares itself to (scripts/refs/lock.json) for changes.

Usage:
  python3 scripts/refs-watch.py --check    one JSON line: {repo: {changed, sha, locked_sha, new_skills, removed_skills, changed_skills}}
  python3 scripts/refs-watch.py --update   write each repo's current head and SKILL.md list into the lock

It never imports anything: a person (or a gbase:plan run) reads what changed, decides what gbase takes,
then runs --update. See plugins/base/references/pstack-sync.md, "Reference watch".
A fetch failure prints {"error": …} and exits 1.
"""
import argparse
import http.client
import json
import os
import subprocess
import sys
import urllib.parse
import urllib.request
from pathlib import Path

LOCK = "scripts/refs/lock.json"


class WatchError(Exception):
    pass


def api(path):
    env = {k: v for k, v in os.environ.items() if k != "GITHUB_TOKEN"}
    try:
        out = subprocess.run(["gh", "api", path], capture_output=True, env=env, timeout=120)
        if out.returncode == 0:
            return json.loads(out.stdout)
        gh_error = out.stderr.decode(errors="replace").strip()[:300]
    except (OSError, subprocess.TimeoutExpired, ValueError) as e:
        gh_error = str(e)
    try:
        with urllib.request.urlopen(f"https://api.github.com/{path}", timeout=60) as r:
            return json.load(r)
    except (OSError, ValueError, http.client.HTTPException) as e:
        raise WatchError(f"{path}: gh: {gh_error}; https: {e}")


def fetch(repo, ref):
    sha = api(f"repos/{repo}/commits/{urllib.parse.quote(ref, safe='/')}")["sha"]
    tree = api(f"repos/{repo}/git/trees/{sha}?recursive=1")
    if tree.get("truncated"):
        raise WatchError(f"{repo}: tree listing truncated; SKILL.md list would be incomplete")
    skills = {e["path"]: e["sha"] for e in tree["tree"]
              if e["type"] == "blob" and (e["path"] == "SKILL.md" or e["path"].endswith("/SKILL.md"))}
    return sha, skills


def load_lock(root):
    return json.loads((root / LOCK).read_text())


def compare(entry, sha, skills):
    old = entry.get("skills", {})
    return {
        "changed": sha != entry.get("sha"),
        "sha": sha,
        "locked_sha": entry.get("sha"),
        "new_skills": sorted(skills.keys() - old.keys()),
        "removed_skills": sorted(old.keys() - skills.keys()),
        "changed_skills": sorted(p for p in skills.keys() & old.keys() if skills[p] != old[p]),
    }


def ref(repo, entry):
    if not entry.get("ref"):
        raise WatchError(f"{repo}: lock entry has no ref")
    return entry["ref"]


def check(root):
    lock = load_lock(root)
    return {repo: compare(entry, *fetch(repo, ref(repo, entry))) for repo, entry in sorted(lock["repos"].items())}


def update(root):
    lock = load_lock(root)
    report = {}
    for repo, entry in sorted(lock["repos"].items()):
        sha, skills = fetch(repo, ref(repo, entry))
        report[repo] = {"sha": sha, "skills": len(skills), "was": entry.get("sha")}
        entry["sha"], entry["skills"] = sha, dict(sorted(skills.items()))
    (root / LOCK).write_text(json.dumps(lock, indent=2, ensure_ascii=False) + "\n")
    return report


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    mode = ap.add_mutually_exclusive_group(required=True)
    mode.add_argument("--check", action="store_true")
    mode.add_argument("--update", action="store_true")
    ap.add_argument("--root", default=str(Path(__file__).resolve().parent.parent))
    args = ap.parse_args(argv)
    root = Path(args.root)
    try:
        print(json.dumps(check(root) if args.check else update(root), ensure_ascii=False))
        return 0
    except (WatchError, KeyError, OSError, ValueError, AttributeError, TypeError) as e:
        print(json.dumps({"error": str(e)}, ensure_ascii=False))
        return 1


if __name__ == "__main__":
    sys.exit(main())
