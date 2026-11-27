#!/usr/bin/env python3
"""How much instruction text a PR run loads into its main session, per route — and the ceiling check.py holds it to.

  python3 scripts/read-budget.py                    the routes of scripts/read-budget.json: files, characters, limit, target
  python3 scripts/read-budget.py --skills           every gbase skill body, largest first
  python3 scripts/read-budget.py --log <log.jsonl>… what real runs loaded (a gbase-run log): skills invoked and plugin files read by the main session
                                                    (a file read through `cat`/`sed` in Bash counts whole, so that part is an upper bound)
  python3 scripts/read-budget.py --ref <git-ref>    measure the routes as of another commit (files missing there count 0)

The unit is characters, not bytes: Korean text is three bytes a character and one token or so either way.
"""
import importlib.util
import json
import re
import subprocess
import sys
from pathlib import Path, PurePosixPath

ROOT = Path(__file__).resolve().parent.parent
BUDGET = ROOT / "scripts" / "read-budget.json"


def text_of(rel, ref=None):
    if ref:
        p = subprocess.run(["git", "-C", str(ROOT), "show", f"{ref}:{rel}"], capture_output=True)
        return p.stdout.decode("utf-8", "replace") if p.returncode == 0 else None
    path = ROOT / rel
    return path.read_text(encoding="utf-8") if path.is_file() else None


def size(rel, ref=None):
    """Characters in a repo file, at `ref` when given; None when it isn't there."""
    text = text_of(rel, ref)
    return None if text is None else len(text)


def listing_rows(patterns, ref=None):
    if ref:
        tree = subprocess.run(["git", "-C", str(ROOT), "ls-tree", "-r", "--name-only", ref], capture_output=True, text=True).stdout.split()
        paths = sorted(f for f in tree if any(PurePosixPath(f).match(pat) for pat in patterns))
    else:
        paths = sorted(p.relative_to(ROOT).as_posix() for pat in patterns for p in ROOT.glob(pat))
    spec = importlib.util.spec_from_file_location("check", Path(__file__).with_name("check.py"))
    check = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(check)
    rows = []
    for rel in paths:
        fm = check.frontmatter(text_of(rel, ref) or "") or {}
        if fm.get("disable-model-invocation", "").lower() in ("true", "yes", "on") or not fm.get("description"):
            continue
        name = Path(rel).parent.name if Path(rel).name == "SKILL.md" else Path(rel).stem
        parts = rel.split("/")
        plugin_dir = "/".join(parts[:next(i for i, p in enumerate(parts) if p in ("skills", "agents", "commands"))])
        manifest = text_of(f"{plugin_dir}/.claude-plugin/plugin.json", ref)
        plugin = json.loads(manifest).get("name", "") if manifest else ""
        listed = f"{plugin}:{name}" if plugin else name
        rows.append((f"{rel} (description)", len(listed) + len(fm["description"])))
    return rows


def route_files(budget, name):
    route = budget["routes"][name]
    inherited = route_files(budget, route["extends"]) if route.get("extends") else []
    return inherited + [f for f in route["reads"] if f not in inherited]


def measure(budget, ref=None):
    """{route or extra: {"files": [(path, chars or None)], "total", "limit", "target"}}"""
    out = {}
    for name, route in budget["routes"].items():
        files = [(f, size(f, ref)) for f in route_files(budget, name)]
        out[name] = {"files": files, "total": sum(n or 0 for _, n in files), "limit": route.get("limit"), "target": route.get("target")}
    for name, extra in budget.get("extras", {}).items():
        files = [(f, size(f, ref)) for f in extra["reads"]] + listing_rows(extra.get("listing", []), ref)
        out[f"+{name}"] = {"files": files, "total": sum(n or 0 for _, n in files), "limit": extra.get("limit"), "target": None}
    return out


def problems(budget=None):
    """What check.py reports: a route over its limit, a listed file that no longer exists, or a limit set below its target."""
    budget = budget or json.loads(BUDGET.read_text(encoding="utf-8"))
    found = []
    for name, m in measure(budget).items():
        for f, n in m["files"]:
            if n is None:
                found.append(f"route {name} lists {f}, which doesn't exist — fix scripts/read-budget.json")
        if m["limit"] is not None and m["total"] > m["limit"]:
            found.append(f"route {name} loads {m['total']:,} characters into the main session, over its limit of {m['limit']:,} "
                         f"(python3 scripts/read-budget.py) — cut something, or move a branch-specific part to a references/ file read only when it applies")
        if m["limit"] is not None and m["target"] is not None and m["limit"] < m["target"]:
            found.append(f"route {name}: limit {m['limit']:,} is below its target {m['target']:,} — set the limit to the target")
    return found


def log_reads(path, plugin_root=ROOT):
    """(skills, files) the main session of one stream-json log loaded: {name: characters}."""
    ids, skills, files = {}, {}, {}

    def add_bash_read(found):
        if len(found) == 1:
            files.setdefault(found[0].relative_to(plugin_root).as_posix() + " (via Bash)", len(found[0].read_text(encoding="utf-8")))

    for line in Path(path).read_text(encoding="utf-8", errors="replace").splitlines():
        try:
            event = json.loads(line)
        except ValueError:
            continue
        if event.get("parent_tool_use_id") is not None or event.get("type") not in ("assistant", "user"):
            continue
        content = (event.get("message") or {}).get("content")
        if isinstance(content, str):
            content = [{"type": "text", "text": content}]
        for block in content or []:
            kind = block.get("type")
            if kind == "tool_use" and block.get("name") == "Skill":
                skills.setdefault(block["input"].get("skill", "?"), 0)
            elif kind == "tool_use" and block.get("name") == "Read":
                target = block["input"].get("file_path", "")
                if re.search(r"/(plugins/[^/]+|\.claude)/(skills|references|commands|agents)/.*\.md$", target):
                    ids[block["id"]] = re.sub(r"^.*?/(plugins/[^/]+/|\.claude/)", r"\1", target)
            elif kind == "tool_use" and block.get("name") == "Bash" and re.search(r"\b(cat|sed|head|tail|less|bat)\b", block["input"].get("command", "")):
                # sessions often `cat` a reference instead of using Read; count the file at its size in this checkout
                for token in re.findall(r"[\w$.{}/~-]*(?:references|skills|commands)/[\w./-]+\.md", block["input"]["command"]):
                    tail = re.sub(r"^.*?((?:skills/[\w-]+/)?(?:references|commands)/|skills/)", r"\1", token)
                    add_bash_read(list(plugin_root.glob(f"plugins/*/{tail}")))
                for name in re.findall(r"\$\{?\w+\}?/([\w-]+\.md)", block["input"]["command"]):  # R=…/references; cat $R/headless.md
                    add_bash_read(list(plugin_root.glob(f"plugins/*/references/{name}")))
            elif kind == "tool_result" and block.get("tool_use_id") in ids:
                text = block.get("content")
                text = text if isinstance(text, str) else "".join(x.get("text", "") for x in text or [] if isinstance(x, dict))
                files[ids[block["tool_use_id"]]] = len(text)
            elif kind == "text":
                m = re.match(r"Base directory for this skill: (\S+)", block.get("text", ""))
                if m:  # the skill's body, as the session received it
                    name = Path(m.group(1)).name
                    key = next((s for s in skills if s.split(":")[-1] == name), name)
                    skills[key] = len(block["text"])
    return skills, files


def main(argv):
    budget = json.loads(BUDGET.read_text(encoding="utf-8"))
    if "--log" in argv:
        totals = []
        for path in argv[argv.index("--log") + 1:]:
            skills, files = log_reads(path)
            total = sum(skills.values()) + sum(files.values())
            totals.append(total)
            print(f"{path}: {total:,} characters")
            for name, n in sorted({**skills, **files}.items(), key=lambda kv: -kv[1]):
                print(f"  {n:>7,}  {name}")
        if len(totals) > 1:
            print(f"median of {len(totals)} runs: {sorted(totals)[len(totals) // 2]:,}")
        return 0
    if "--skills" in argv:
        rows = [(size(p.relative_to(ROOT).as_posix()), p.parent.name) for p in sorted((ROOT / "plugins/base/skills").glob("*/SKILL.md"))]
        print("\n".join(f"{n:>7,}  {name}" for n, name in sorted(rows, reverse=True)))
        return 0
    ref = argv[argv.index("--ref") + 1] if "--ref" in argv else None
    for name, m in measure(budget, ref).items():
        limit = f"limit {m['limit']:,}" if m["limit"] is not None else "no limit"
        target = f", target {m['target']:,}" if m["target"] is not None else ""
        print(f"{name}: {m['total']:,} characters ({limit}{target})")
        for f, n in m["files"]:
            print(f"  {n if n is not None else 0:>7,}  {f}{'' if n is not None else '  (not there)'}")
    if not ref:
        for p in problems(budget):
            print(f"FAIL {p}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
