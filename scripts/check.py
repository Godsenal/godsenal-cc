#!/usr/bin/env python3
"""Repo checks for the godsenal marketplace — rules from CLAUDE.md that CI enforces.

Usage: python3 scripts/check.py [--base <git-ref>]
  --base  also check that every plugin with changed files bumped its version vs <git-ref>
"""
import json
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
MARKETPLACE = ROOT / ".claude-plugin" / "marketplace.json"
MAX_SKILL_LINES = 500
MAX_DESCRIPTION = 1536
LANG_BLOCK = "## 출력 언어"

# Cross-skill contracts: each token must appear (case-insensitive) in every listed file.
# Changing one side without the other silently breaks the caller.
def skill(name):
    return f"plugins/base/skills/{name}/SKILL.md"


BRANCH_PR = "plugins/base/commands/branch-pr.md"
CONTRACTS = [
    ("⚠️ requires ordered rollout", [skill("compat-check"), BRANCH_PR]),
    # compat-check's output template itself, not just prose that mentions the tokens
    ("- `✅ no special deploy ordering needed`", [skill("compat-check")]),
    ("- `⚠️ requires ordered rollout`", [skill("compat-check")]),
    ("start at stage 2", [skill("go"), skill("review")]),
    ("defer, don't ask", [skill("go"), skill("review")]),
    ("--no-review", [skill("go"), skill("monitor")]),
    ("--draft", [skill("go"), skill("monitor")]),
    ("gbase:verify", [skill("setup"), skill("go")]),
    ("verification:", [skill("go"), BRANCH_PR]),
    (".claude/skills/verify-", [skill("create-verify"), skill("go")]),
]

errors = []


def fail(path, msg):
    p = Path(path)
    errors.append(f"{p.relative_to(ROOT) if p.is_absolute() else p}: {msg}")


def load_json(path):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as e:
        fail(path, f"invalid JSON — {e}")
        return None


def frontmatter(text):
    """Minimal YAML frontmatter reader: top-level `key: value`, quoted values, and block scalars."""
    m = re.match(r"---\n(.*?)\n---\n", text, re.S)
    if not m:
        return None
    fields, key, block = {}, None, []
    for line in m.group(1).split("\n"):
        top = re.match(r"([A-Za-z0-9_-]+):\s*(.*)$", line)
        if top and not line.startswith(" "):
            if key and block:
                fields[key] = " ".join(block)
            key, value, block = top.group(1), top.group(2).strip(), []
            if re.fullmatch(r"[>|][-+0-9]*", value):
                continue
            block = [value.strip("\"'")]  # plain scalars may wrap onto indented lines too
        elif key and line.strip():
            block.append(line.strip())
    if key and block:
        fields[key] = " ".join(block)
    return fields


def check_plugins():
    market = load_json(MARKETPLACE)
    if not market:
        return {}
    versions = {}
    for entry in market.get("plugins", []):
        pdir = (ROOT / entry["source"]).resolve()
        manifest = load_json(pdir / ".claude-plugin" / "plugin.json")
        if not manifest:
            continue
        if manifest.get("name") != entry["name"]:
            fail(MARKETPLACE, f"entry {entry['name']!r} points at plugin named {manifest.get('name')!r}")
        if manifest.get("version") != entry.get("version"):
            fail(MARKETPLACE, f"{entry['name']} version {entry.get('version')} != plugin.json {manifest.get('version')}")
        versions[entry["name"]] = (pdir, entry.get("version"))
        check_skills(pdir)
    return versions


def check_skills(pdir):
    for skill in sorted(pdir.glob("skills/*/SKILL.md")):
        text = skill.read_text(encoding="utf-8")
        fm = frontmatter(text)
        if fm is None:
            fail(skill, "missing YAML frontmatter")
            continue
        if fm.get("name") != skill.parent.name:
            fail(skill, f"frontmatter name {fm.get('name')!r} != directory {skill.parent.name!r}")
        desc = fm.get("description", "")
        if not desc:
            fail(skill, "missing description")
        elif len(desc) > MAX_DESCRIPTION:
            fail(skill, f"description is {len(desc)} chars (listing truncates at {MAX_DESCRIPTION})")
        lines = text.count("\n") + 1
        if lines > MAX_SKILL_LINES:
            fail(skill, f"{lines} lines (keep under {MAX_SKILL_LINES}; move reference material out)")
        if LANG_BLOCK not in text:
            fail(skill, f"missing `{LANG_BLOCK}` block")
        for ref in re.findall(r"\]\(((?:references|scripts)/[^)#\s]+)\)", text):
            if not (skill.parent / ref).exists():
                fail(skill, f"links missing file {ref}")
    for cmd in sorted(pdir.glob("commands/*.md")):
        if LANG_BLOCK not in cmd.read_text(encoding="utf-8"):
            fail(cmd, f"missing `{LANG_BLOCK}` block")


def check_contracts():
    texts = {}
    for token, files in CONTRACTS:
        for f in files:
            path = ROOT / f
            if not path.exists():
                fail(f, f"contract file missing (token {token!r})")
                continue
            if f not in texts:
                texts[f] = path.read_text(encoding="utf-8").lower()
            if token not in texts[f]:
                fail(f, f"contract token {token!r} missing — update both sides: {', '.join(files)}")


def git(*args):
    return subprocess.run(["git", "-C", str(ROOT), *args], capture_output=True, text=True, check=True).stdout


def check_version_bumps(base, versions):
    # working tree vs merge-base, plus untracked files: `go` runs this before anything is committed
    merge_base = git("merge-base", base, "HEAD").strip()
    changed = git("diff", "--name-only", merge_base).split() + git("ls-files", "--others", "--exclude-standard").split()
    for pdir, version in versions.values():
        rel = pdir.relative_to(ROOT).as_posix() + "/"
        if not any(p.startswith(rel) for p in changed):
            continue
        try:
            old = json.loads(git("show", f"{base}:{rel}.claude-plugin/plugin.json"))["version"]
        except subprocess.CalledProcessError:
            continue  # new plugin
        if old == version:
            fail(rel, f"files changed but version still {version} — bump plugin.json and marketplace.json")


def main():
    args = sys.argv[1:]
    base = args[args.index("--base") + 1] if "--base" in args else None
    versions = check_plugins()
    check_contracts()
    if base:
        check_version_bumps(base, versions)
    if errors:
        print("\n".join(f"FAIL {e}" for e in errors))
        sys.exit(1)
    print(f"PASS ({len(versions)} plugins)")


if __name__ == "__main__":
    main()
