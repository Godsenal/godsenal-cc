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
ORCHESTRATOR = "plugins/base/references/orchestrator.md"
HEADLESS = "plugins/base/references/headless.md"
SESSION_HOOK = "plugins/base/hooks/session-start.md"
FACTORY = "plugins/base/.claude-plugin/factory.json"
RUNNER = "scripts/gbase-run"
CONTRACTS = [
    ("⚠️ requires ordered rollout", [skill("compat-check"), BRANCH_PR]),
    # compat-check's output template itself, not just prose that mentions the tokens
    ("- `✅ no special deploy ordering needed`", [skill("compat-check")]),
    ("- `⚠️ requires ordered rollout`", [skill("compat-check")]),
    ("start at stage 2", [skill("go"), skill("review")]),
    ("defer, don't ask", [skill("go"), skill("review")]),
    ("--no-review", [skill("go"), skill("monitor")]),
    ("--draft", [skill("go"), skill("monitor")]),
    ("--merge", [skill("work"), skill("go"), skill("monitor")]),
    ("gbase:verify", [skill("setup"), skill("go")]),
    ("verification:", [skill("go"), BRANCH_PR]),
    ("risk:", [skill("go"), BRANCH_PR]),
    ("intent:", [skill("pause"), skill("pickup"), skill("go"), BRANCH_PR]),
    ("git reset --soft", [BRANCH_PR]),
    (".claude/skills/verify-", [skill("create-verify"), skill("go")]),
    (".claude/skills/verify/", [skill("create-verify"), skill("go"), skill("setup")]),
    ("ship-owner: orchestrator", [skill("go"), BRANCH_PR]),
    ("pr-body-file:", [skill("go"), BRANCH_PR]),
    ("ship: local", [BRANCH_PR, ORCHESTRATOR]),
    ("pr 본문 초안:", [skill("go"), BRANCH_PR, ORCHESTRATOR, RUNNER]),
    ("--until-settled", [skill("monitor"), ORCHESTRATOR]),
    ("settle: 수렴", [skill("monitor"), ORCHESTRATOR]),
    ("결정 필요:", [HEADLESS, ORCHESTRATOR, RUNNER]),
    ("agent_evidence_file", [skill("go"), skill("reproduce"), ORCHESTRATOR]),
    ("gbase:reproduce", [skill("bug-fix"), skill("reproduce")]),
    # the session hook routes to work and names the agent types work dispatches
    ("`gbase:work`", [SESSION_HOOK]),
    ("gbase:scout", [skill("work"), SESSION_HOOK]),
    ("gbase:worker", [skill("work"), SESSION_HOOK]),
    ("changes a signature other files call", [skill("work"), SESSION_HOOK]),
    ("gbase:unslop", [BRANCH_PR, skill("work")]),
    # review2 runs review twice on one tree; report only keeps the two sessions from editing
    ("report only", [skill("review"), FACTORY]),
    # the runner merges review2 by parsing review's report table
    ("# | severity | file:line | finding | action", [skill("review"), RUNNER]),
]

# a manifest slot's fields; anything else is a typo the orchestrator would silently ignore
SLOT_REQUIRED = {"invoke", "env", "notes"}
SLOT_OPTIONAL = {"setup", "reads", "models"}

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
        check_agents(pdir)
        check_hooks(pdir)
        check_references(pdir)
        check_factory(pdir)
    return versions


def check_skills(pdir):
    for skill in sorted(pdir.glob("skills/*/SKILL.md")):
        text = skill.read_text(encoding="utf-8")
        desc = check_frontmatter(skill, text, skill.parent.name)
        if desc is None:
            continue
        if len(desc) > MAX_DESCRIPTION:
            fail(skill, f"description is {len(desc)} chars (listing truncates at {MAX_DESCRIPTION})")
        lines = text.count("\n") + 1
        if lines > MAX_SKILL_LINES:
            fail(skill, f"{lines} lines (keep under {MAX_SKILL_LINES}; move reference material out)")
        if LANG_BLOCK not in text:
            fail(skill, f"missing `{LANG_BLOCK}` block")
        check_links(skill, text)
    for cmd in sorted(pdir.glob("commands/*.md")):
        text = cmd.read_text(encoding="utf-8")
        if LANG_BLOCK not in text:
            fail(cmd, f"missing `{LANG_BLOCK}` block")
        check_links(cmd, text)


def check_frontmatter(path, text, name):
    """Frontmatter exists, its name matches, and it has a description; returns the description, or None without frontmatter."""
    fm = frontmatter(text)
    if fm is None:
        fail(path, "missing YAML frontmatter")
        return None
    if fm.get("name") != name:
        fail(path, f"frontmatter name {fm.get('name')!r} != {name!r}")
    desc = fm.get("description", "")
    if not desc:
        fail(path, "missing description")
    return desc


def check_agents(pdir):
    for agent in sorted(pdir.glob("agents/*.md")):
        check_frontmatter(agent, agent.read_text(encoding="utf-8"), agent.stem)


def check_references(pdir):
    """Every `gbase:<name>` the session hook names and every gbase subagent_type resolves to a skill, agent, or command."""
    plugin = (load_json(pdir / ".claude-plugin" / "plugin.json") or {}).get("name", "")
    hook = pdir / "hooks" / "session-start.md"
    sources = [(hook, rf"`{plugin}:([a-z0-9-]+)`")] if hook.exists() else []
    sources += [(md, rf'subagent_type: "{plugin}:([a-z0-9-]+)"') for md in sorted(pdir.glob("skills/*/SKILL.md"))]
    for path, pattern in sources:
        for name in re.findall(pattern, path.read_text(encoding="utf-8")):
            if not any((pdir / p).exists() for p in (f"skills/{name}/SKILL.md", f"agents/{name}.md", f"commands/{name}.md")):
                fail(path, f"names {plugin}:{name}, which is no skill, agent, or command")


def check_hooks(pdir):
    path = pdir / "hooks" / "hooks.json"
    if not path.exists():
        return
    for event in (load_json(path) or {}).get("hooks", {}).values():
        for group in event:
            for hook in group.get("hooks", []):
                for script in re.findall(r"\$\{CLAUDE_PLUGIN_ROOT\}/([^\"'\s]+)", hook.get("command", "")):
                    if not (pdir / script).is_file():
                        fail(path, f"hook command runs missing file {script}")


def check_links(path, text):
    for ref in re.findall(r"\]\(((?:\.\./)+[^)#\s]+|(?:references|scripts)/[^)#\s]+)", text):
        if not (path.parent / ref).exists():
            fail(path, f"links missing file {ref}")


def allowed_tools(text):
    m = re.search(r"^allowed-tools:(.*)$", text, re.M)
    return m.group(1) if m else ""


def check_factory(pdir):
    """A plugin that ships .claude-plugin/factory.json promises orchestrators headless skills and real slots."""
    path = pdir / ".claude-plugin" / "factory.json"
    if not path.exists():
        return
    manifest = load_json(path)
    if not manifest:
        return
    if manifest.get("schema") != 1:
        fail(path, f"schema {manifest.get('schema')!r} != 1")
    contract = pdir / str(manifest.get("contract", ""))
    if not contract.is_file():
        fail(path, f"contract {manifest.get('contract')!r} is not a file in the plugin")
    env = manifest.get("env", {})
    contract_text = contract.read_text(encoding="utf-8") if contract.is_file() else ""
    for name, meaning in env.items():
        if not isinstance(meaning, str) or not meaning:
            fail(path, f"env {name} needs a one-line meaning")
        if f"`{name}`" not in contract_text:
            fail(path, f"env {name} is not documented in {manifest.get('contract')}")
    plugin = load_json(pdir / ".claude-plugin" / "plugin.json") or {}
    for slot, spec in manifest.get("slots", {}).items():
        keys = set(spec)
        if SLOT_REQUIRED - keys or keys - SLOT_REQUIRED - SLOT_OPTIONAL:
            fail(path, f"slot {slot}: fields {sorted(keys)}, want {sorted(SLOT_REQUIRED)} + optional {sorted(SLOT_OPTIONAL)}")
        for var in spec.get("env", []):
            if var not in env:
                fail(path, f"slot {slot}: env {var} isn't declared in the top-level env")
        models = spec.get("models")
        if models is not None and not (isinstance(models, list) and len(models) >= 2 and all(isinstance(m, str) and m for m in models)):
            fail(path, f"slot {slot}: models must list two or more model names")
        if not spec.get("notes"):
            fail(path, f"slot {slot}: empty notes")
        if spec.get("invoke") is None and not spec.get("reads"):
            fail(path, f"slot {slot}: invoke null needs reads")
        for field in ("invoke", "setup"):
            cmd = spec.get(field)
            if cmd is None:
                continue
            m = re.match(rf"/{re.escape(plugin.get('name', ''))}:([a-z0-9-]+)", cmd)
            if not m:
                fail(path, f"slot {slot}: {field} {cmd!r} isn't a /{plugin.get('name')}:<skill> command")
            elif not (pdir / "skills" / m.group(1) / "SKILL.md").exists() and not (pdir / "commands" / f"{m.group(1)}.md").exists():
                fail(path, f"slot {slot}: {field} names missing skill {m.group(1)}")
    for md in sorted(pdir.glob("skills/*/SKILL.md")) + sorted(pdir.glob("commands/*.md")):
        text = md.read_text(encoding="utf-8")
        # a command with no allowed-tools line can ask too; the 출력 언어 block's own mention doesn't count
        can_ask = "AskUserQuestion" in allowed_tools(text) or "AskUserQuestion" in text.replace("`AskUserQuestion`의 질문", "")
        if can_ask and "references/headless.md" not in text:
            fail(md, "can ask but doesn't point at references/headless.md (orchestrators run it with AGENT_HEADLESS=1)")


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
