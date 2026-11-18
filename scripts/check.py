#!/usr/bin/env python3
"""Repo checks for the godsenal marketplace — rules from CLAUDE.md that CI enforces.

Usage: python3 scripts/check.py [--base <git-ref>]
  --base  also check that every plugin with changed files bumped its version vs <git-ref>
"""
import importlib.util
import json
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
MARKETPLACE = ROOT / ".claude-plugin" / "marketplace.json"
MAX_SKILL_LINES = 500
MAX_DESCRIPTION = 1536
MAX_LANG_BLOCK = 560  # the full rule is references/output-language.md; a skill body keeps a line or two
LANG_BLOCK = "## 출력 언어"

# Cross-skill contracts: each token must appear (case-insensitive) in every listed file.
# Changing one side without the other silently breaks the caller.
def skill(name):
    return f"plugins/base/skills/{name}/SKILL.md"


def shorts(name):
    return f"plugins/shorts/skills/{name}/SKILL.md"


BRANCH_PR = skill("branch-pr")
# go's branches: the pre-PR review (medium/high), the rest of the verification gate, --draft/--merge, and orchestrator runs
GO_REVIEW = "plugins/base/skills/go/references/review.md"
GO_VERIFY = "plugins/base/skills/go/references/verify.md"
GO_HIGH = "plugins/base/skills/go/references/high.md"  # read on `high` only: the independent behavior check, order-of-events checks
REVIEW_PROVEN = "plugins/base/skills/review/references/proven.md"
GO_DRAFT_MERGE = "plugins/base/skills/go/references/draft-merge.md"
GO_ORCH = "plugins/base/skills/go/references/orchestrated.md"
WORK_PLAYBOOKS = "plugins/base/skills/work/references/playbooks.md"
PLAYBOOK_DIR = "plugins/base/skills/poteto-mode/playbooks"
# the parts of branch-pr and monitor that only some runs read; a token lives where that branch is written
PR_BODY = "plugins/base/skills/branch-pr/references/pr-body.md"
LOCAL_MODE = "plugins/base/skills/branch-pr/references/local-mode.md"
SHIP_PREP = "plugins/base/skills/branch-pr/scripts/ship-prep"
SETTLE = "plugins/base/skills/monitor/references/settle.md"
MERGE = "plugins/base/skills/monitor/references/merge.md"
CONFLICTS = "plugins/base/skills/monitor/references/conflicts.md"
COMMENTS = "plugins/base/skills/monitor/references/comments.md"
PR_STATUS = "plugins/base/skills/monitor/scripts/pr-status"
ORCHESTRATOR = "plugins/base/references/orchestrator.md"
HEADLESS = "plugins/base/references/headless.md"
HARNESS = "plugins/base/references/harness.md"
SESSION_HOOK = "plugins/base/hooks/session-start.md"
FACTORY = "plugins/base/.claude-plugin/factory.json"
POLISH_COMMENTS = "plugins/base/skills/polish/references/comments.md"  # polish's Pass 0: pstack's no-comments, read by path
ADDED_COMMENTS = "plugins/base/skills/polish/scripts/added-comments"
RUNNER = "scripts/gbase-run"
CONVENTIONS = "plugins/base/references/conventions.md"
ENVIRONMENT = "plugins/base/references/environment.md"
SETUP_ENV = "plugins/base/skills/setup/references/explore-environment.md"
TRACKER_FREE = [skill("work"), skill("go"), BRANCH_PR, skill("monitor"), PR_BODY, LOCAL_MODE, SHIP_PREP, GO_REVIEW, GO_VERIFY, GO_HIGH,
                GO_DRAFT_MERGE, GO_ORCH, SETTLE, MERGE, CONFLICTS, COMMENTS, PR_STATUS]
TRACKER_NAMES = r"\b(jira|acli|atlassian|linear|asana|trello|youtrack)\b"
PSTACK_SYNC = "scripts/pstack-sync.py"
PSTACK_DOC = "plugins/base/references/pstack-sync.md"
PSTACK_ADAPTER = "plugins/base/references/pstack-adapter.md"
RUNNER_DOC = "plugins/base/references/runner.md"  # the runner's usage and result.json, split out of orchestrator.md
CONTRACTS = [
    ("⚠️ requires ordered rollout", [skill("compat-check"), BRANCH_PR]),
    # compat-check's output template itself, not just prose that mentions the tokens
    ("- `✅ no special deploy ordering needed`", [skill("compat-check")]),
    ("- `⚠️ requires ordered rollout`", [skill("compat-check")]),
    ("start at stage 2", [GO_REVIEW, skill("review")]),
    ("defer, don't ask", [GO_REVIEW, skill("review"), skill("monitor")]),
    ("one skeptic for low/medium", [skill("go"), GO_REVIEW, GO_ORCH, skill("review")]),
    # polish, review, compat-check, and unslop run in subagents so their bodies stay out of the main session
    ('skill(skill: "gbase:polish"', [skill("go")]),
    (r'skill(skill: \"gbase:review\"', [GO_REVIEW]),  # review.md writes the call inside a quoted prompt, so the backslash is part of the token
    ('skill(skill: "gbase:review"', [skill("monitor")]),
    ('skill(skill: "gbase:compat-check"', [BRANCH_PR]),
    ('skill(skill: "gbase:unslop"', [BRANCH_PR, skill("work")]),
    ("awaiting confirm", [skill("go"), skill("polish"), COMMENTS, CONFLICTS]),  # every polish launch says what a subagent that can't ask does
    ("printenv | grep '^agent_'", [skill("go"), GO_ORCH]),  # in go's Step 1 prose, runnable as written (a table cell needs the pipe escaped)
    ("subagent that can't ask", [skill("compat-check")]),
    # go's body names the reference each branch reads
    ("references/review.md", [skill("go")]),
    ("references/verify.md", [skill("go")]),
    ("references/draft-merge.md", [skill("go")]),
    # high adds its verification in one file: an agent that didn't write the code runs the behavior check, and an open check holds the merge
    ("references/high.md", [skill("go")]),
    ("high.md", [GO_VERIFY]),
    ("risk line", [GO_HIGH, CONFLICTS]),  # monitor learns the tier from the PR body branch-pr wrote, not from a flag
    ("statechart", [GO_HIGH]),
    ("create-formal-verification-skill", [GO_HIGH]),
    # a skipped behavior check is unverified, not passed: a (확인) item in the PR, `open` in the evidence file, `unverified` in result.json
    ("behavior: skip", [skill("work"), GO_VERIFY, GO_HIGH, BRANCH_PR, PR_BODY, SHIP_PREP, ORCHESTRATOR]),
    ("(확인)", [GO_VERIFY, PR_BODY, SHIP_PREP, ORCHESTRATOR]),
    ('== "open"', [SHIP_PREP, RUNNER]),
    ("unverified", [GO_VERIFY, SHIP_PREP, RUNNER, RUNNER_DOC, ORCHESTRATOR]),
    # after a rebase or base merge on a high PR, pr-status compares patch ids and its next: line says whether to re-verify
    ("git patch-id", [PR_STATUS, CONFLICTS, ORCHESTRATOR]),
    ("pr-status script> patch", [CONFLICTS]),
    ("nothing to re-verify", [PR_STATUS, CONFLICTS]),
    ("one verifier", [PR_STATUS, CONFLICTS]),
    # review marks a high finding a run proved, inside the finding cell, and keeps one no run could reach
    ("references/proven.md", [skill("review")]),
    ("실행으로 확인됨", [REVIEW_PROVEN]),
    ("실행 증거 없음", [REVIEW_PROVEN]),
    ("references/orchestrated.md", [skill("go")]),
    # work hands go its surface verification so go doesn't run the behavior check twice
    ("`behavior:`", [skill("work"), skill("go"), GO_VERIFY]),
    ("--no-review", [skill("go"), skill("monitor")]),
    ("--draft", [skill("go"), GO_DRAFT_MERGE, skill("monitor")]),
    ("--merge", [skill("work"), skill("go"), GO_DRAFT_MERGE, GO_ORCH, skill("monitor")]),
    ("gbase:verify", [skill("setup"), skill("go"), GO_VERIFY]),
    ("verification:", [skill("go"), BRANCH_PR]),
    ("risk:", [skill("go"), BRANCH_PR]),
    ("deferred:", [skill("go"), BRANCH_PR]),
    ("## review focus", [skill("go"), GO_DRAFT_MERGE, BRANCH_PR, PR_BODY, SHIP_PREP, ORCHESTRATOR]),
    ("intent:", [skill("pause"), skill("pickup"), skill("go"), BRANCH_PR]),
    ("git reset --soft", [BRANCH_PR]),
    # ship-prep does the reset; its marker is the same wip: + Intent: pair pause writes
    ('"wip:"', [SHIP_PREP]),
    ("refs/gbase/backup/", [BRANCH_PR, SHIP_PREP, RUNNER]),
    (".claude/skills/verify-", [skill("create-verify"), GO_VERIFY]),
    (".claude/skills/verify/", [skill("create-verify"), GO_VERIFY, skill("setup")]),
    ("ship-owner: orchestrator", [GO_ORCH, BRANCH_PR]),
    ("pr-body-file:", [GO_ORCH, BRANCH_PR]),
    ("ship: local", [LOCAL_MODE, ORCHESTRATOR, SETTLE]),
    ("ship: skip —", [HEADLESS, ORCHESTRATOR]),  # a shipping step the caller put out of scope, not a decision
    ("pr 본문 초안:", [GO_ORCH, LOCAL_MODE, ORCHESTRATOR, RUNNER, SETTLE]),
    ("--until-settled", [skill("monitor"), SETTLE, GO_ORCH, ORCHESTRATOR]),
    # agent-owned runs: branch-pr prints the PR URL, go carries it up, the runner parses it into pr_url
    ("`pr: <url>`", [skill("go"), GO_ORCH, BRANCH_PR, ORCHESTRATOR, RUNNER, FACTORY]),
    ('print(f"pr: {', [SHIP_PREP]),  # the script prints the line the skill promises
    ("pr_url", [RUNNER_DOC, RUNNER]),
    # conventions.md holds the one setting > convention > default order; the runner reads its branch prefix key
    ("gbase.branchprefix", [CONVENTIONS, RUNNER_DOC, RUNNER]),
    ("references/conventions.md", [BRANCH_PR, MERGE]),
    ("gbase.conventions", [CONVENTIONS, ENVIRONMENT, skill("work"), SHIP_PREP, SETUP_ENV]),
    ("references/environment.md", [skill("work"), skill("setup"), SETUP_ENV]),
    ("(environment.md)", [CONVENTIONS]),
    ("references/explore-environment.md", [skill("setup")]),
    ("`environment:` line", [ENVIRONMENT]), ('"environment: ', [SHIP_PREP]),
    ("shipping it", [ENVIRONMENT, SHIP_PREP]),
    ("## write-back", [ENVIRONMENT]),
    ('"fetch the ticket"', [ENVIRONMENT]),
    ("link the pr on the ticket", [ENVIRONMENT, SETUP_ENV]),
    ("ticket: <key> → not read", [ENVIRONMENT]),
    ("is not permission", [ENVIRONMENT]),
    ("draft only", [SETUP_ENV]),
    ("settle: 수렴", [SETTLE, PR_STATUS, ORCHESTRATOR]),
    ("settle: 미확정", [SETTLE, PR_STATUS, ORCHESTRATOR]),
    ("settle: 사람 필요", [SETTLE, PR_STATUS, ORCHESTRATOR]),
    # monitor and branch-pr act on their scripts' output lines: a line a skill or reference names is one the script prints
    ('"conflict — ', [PR_STATUS]), ("| `conflict` |", [skill("monitor")]),
    ('"comments — ', [PR_STATUS]), ("| `comments` |", [skill("monitor")]),
    ('"ci — ', [PR_STATUS]), ("| `ci` |", [skill("monitor")]),
    ('"notes — ', [PR_STATUS]), ("| `notes` |", [skill("monitor")]),
    ('"settled — ', [PR_STATUS]), ("| `settled` |", [skill("monitor")]),
    ('"limit — ', [PR_STATUS]), ("`next: limit`", [SETTLE]),
    ('"give up — ', [PR_STATUS]), ("`give up`", [skill("monitor"), SETTLE]),
    ('"unstarted — ', [PR_STATUS]), ("`unstarted`", [skill("monitor")]),
    ("merge: gate passed", [PR_STATUS, MERGE]),
    ("merge: not now", [PR_STATUS, MERGE]),
    ("merge: retarget stacked pr first", [PR_STATUS, MERGE]),
    ("--handled", [PR_STATUS, SETTLE]),
    ('"ask: ', [SHIP_PREP]), ("`ask:` lines", [BRANCH_PR]),
    ("branch plan:", [SHIP_PREP, BRANCH_PR]),
    ("--partial", [SHIP_PREP, BRANCH_PR]),
    ("--remote", [SHIP_PREP, BRANCH_PR]),
    ("ship-prep start --local", [LOCAL_MODE]), ("ship-prep check", [LOCAL_MODE]), ("ship-prep assets", [PR_BODY, LOCAL_MODE]),
    ("scripts/pr-status", [skill("monitor")]),
    ("references/settle.md", [skill("monitor")]),
    ("references/merge.md", [skill("monitor")]),
    ("references/comments.md", [skill("monitor"), PR_STATUS]),
    ("references/conflicts.md", [skill("monitor"), PR_STATUS]),
    ("verified-locally", [GO_DRAFT_MERGE, SETTLE, MERGE, PR_STATUS]),
    ("scripts/ship-prep", [BRANCH_PR]),
    ("references/pr-body.md", [BRANCH_PR]),
    ("references/local-mode.md", [BRANCH_PR]),
    ("compat: run", [BRANCH_PR, SHIP_PREP]),
    ("compat: skip", [BRANCH_PR, SHIP_PREP]),
    ("결정 필요:", [HEADLESS, ORCHESTRATOR, RUNNER]),
    # headless forbids wakeups in prose; the runner enforces it by denying the tools
    ("schedulewakeup,croncreate", [HEADLESS, RUNNER_DOC, RUNNER]),
    # bare task runs load no skill: the runner (and a bot's direct template, via harness.md) carries the forbid list
    ("대표자·본인 확인 체크", [HEADLESS, ORCHESTRATOR, RUNNER, HARNESS]),
    # the runner splits decision lines on these keys into recommend / options / human
    ("(추천:", [HEADLESS, RUNNER]),
    ("다른 선택지", [HEADLESS, RUNNER]),
    ("사람이 할 일", [HEADLESS, RUNNER]),
    # settle keeps fixes local and pushes only when the agent owns shipping
    ("agent_ship_owner=orchestrator", [GO_ORCH, skill("monitor"), SETTLE, skill("review"), ORCHESTRATOR]),
    ("푸시 대기:", [SETTLE, ORCHESTRATOR]),
    ("agent_evidence_file", [GO_ORCH, skill("reproduce"), SETTLE, ORCHESTRATOR]),
    ("gbase:reproduce", [skill("bug-fix"), skill("reproduce")]),
    # the session hook routes to work and names the agent types work dispatches
    ("`gbase:work`", [SESSION_HOOK]),
    ("gbase:scout", [skill("work"), SESSION_HOOK]),
    ("gbase:worker", [skill("work"), SESSION_HOOK]),
    ("changes a signature other files call", [skill("work"), SESSION_HOOK]),
    ("a diagnosis from a trace or profile", [skill("work"), SESSION_HOOK]),
    ("spans several prs", [skill("work"), SESSION_HOOK]),
    # work is poteto-mode inside gbase: it routes to pstack's playbooks and reads their Cursor names through playbooks.md
    ("../poteto-mode/playbooks/", [skill("work")]),
    ("references/playbooks.md", [skill("work")]),
    ("pstack-adapter.md", [WORK_PLAYBOOKS]),
    ("benchmark-checklist", [skill("work")]),
    ("root cause before smallest", [skill("work")]),
    ("references/correction.md", [skill("work")]),
    ("used_by", [PSTACK_SYNC, PSTACK_DOC]),
    # polish's Pass 0 is pstack's no-comments: the script decides whether it runs, go passes the tier and carries what stays open
    ("next: comment pass", [ADDED_COMMENTS, skill("polish"), POLISH_COMMENTS]),
    ("next: skip", [ADDED_COMMENTS, skill("polish")]),
    ("next: read the diff yourself", [ADDED_COMMENTS, skill("polish")]),
    ("scripts/added-comments", [skill("polish")]),
    ("references/comments.md", [skill("polish"), ADDED_COMMENTS]),
    ("../../no-comments/skill.md", [POLISH_COMMENTS]),
    ("gbase:comment-sicko", [POLISH_COMMENTS]),
    ("risk: <tier>", [skill("go")]),
    ("stays deleted", [skill("go")]),  # go's main session once restored a constraint comment polish had deleted
    ("`comments:`", [skill("go"), GO_VERIFY, GO_DRAFT_MERGE, POLISH_COMMENTS]),
    ("comments: skip —", [ADDED_COMMENTS, skill("polish")]),
    ("don't encode", [POLISH_COMMENTS]),
    ('"skills/polish/references/comments.md"', ["scripts/pstack/lock.json"]),
    # content runs report lessons instead of editing the harness; the runner hands them to a work run
    ("교훈:", [shorts("content-common"), shorts("shorts-common"), skill("design-taste"), ORCHESTRATOR, RUNNER, FACTORY]),
    # mockup and gapp's design load the user's taste rules before drawing
    # work loads the taste rules before screen work, and its workers do too (they don't inherit loaded skills)
    ("gbase:design-taste", [skill("mockup"), "plugins/app/skills/design/SKILL.md", skill("work"),
                            "plugins/base/skills/work/references/workers.md", "plugins/base/agents/worker.md"]),
    # evidence records what a check ran on; a `differs:` input becomes a Review focus item
    ("`input`", [ORCHESTRATOR, GO_VERIFY, GO_ORCH, skill("reproduce")]),
    ("differs:", [ORCHESTRATOR, GO_VERIFY, skill("reproduce"), BRANCH_PR, PR_BODY]),
    ("input differs from report", [ORCHESTRATOR, skill("reproduce")]),
    ("conflict resolution unreviewed", [CONFLICTS]),
    ("--exclusive", [RUNNER_DOC, RUNNER]),
    # work's size gate reports the slices it left; the runner reads them into followups, and asks a capped run for them
    ("남은 작업:", [skill("work"), ORCHESTRATOR, RUNNER, RUNNER_DOC]),
    ("--max-turns", [RUNNER_DOC, RUNNER]),
    # plan reports its file and slices; the runner reads them into plan_file and followups
    ("`plan: <absolute path>`", [skill("plan"), ORCHESTRATOR]),
    ("plan_file", [RUNNER_DOC, RUNNER]),
    ("`gbase:plan`", [SESSION_HOOK, skill("work")]),
    ("--max-budget-usd", [RUNNER_DOC, RUNNER]),
    # bots start background runs with this one line, not a long nohup claude -p a permission classifier blocks
    ("gbase-run start", [RUNNER_DOC, RUNNER, FACTORY, "README.md"]),
    # settle's one rebase exception, so it stays one rule and not an open door
    ("explicitly asks to rebase", [SETTLE, ORCHESTRATOR, FACTORY, "README.md"]),
    # the runner reads mockup's report lines into result.json
    ("mockup url:", [skill("mockup"), RUNNER, ORCHESTRATOR]),
    ("mockup shots:", [skill("mockup"), RUNNER, ORCHESTRATOR]),
    # mockup stays out of work/go runs (company repos included): explicit /gbase:mockup or --slot mockup only
    ("disable-model-invocation: true", [skill("mockup")]),
    # review2 runs review twice on one tree; report only keeps the two sessions from editing
    ("report only", [skill("review"), FACTORY]),
    # the runner merges review2 by parsing review's report table
    ("# | severity | file:line | finding | action", [skill("review"), RUNNER]),
    # pstack sync: the daily routine parses --check's fields; every followed skill links the adapter the script names
    ("skills_changed", [PSTACK_SYNC, PSTACK_DOC]),
    ("custom_changed", [PSTACK_SYNC, PSTACK_DOC]),
    ("new_upstream", [PSTACK_SYNC, PSTACK_DOC]),
    ("scripts_changed", [PSTACK_SYNC, PSTACK_DOC]),
    ("references/pstack-adapter.md", [PSTACK_SYNC, PSTACK_DOC]),
    # the adapter sends every shipping step of a pstack playbook through go, and questions through headless.md
    ("gbase:go", [PSTACK_ADAPTER, WORK_PLAYBOOKS]),
    ("headless.md", [PSTACK_ADAPTER]),
    # gshorts format skills defer every-video rules to shorts-common; its feedback intake names the format skills
    ("shorts-common", [shorts("foreign-clip-short"), shorts("top3-compilation-short")]),
    ("foreign-clip-short", [shorts("shorts-common"), shorts("top3-compilation-short")]),
    ("top3-compilation-short", [shorts("shorts-common")]),
    # content-common holds rules for every piece of content; shorts-common, instagram-card-news, naver-blog, threads-voice, x-voice, and comment-guide defer to it
    ("content-common", [shorts("shorts-common"), shorts("instagram-card-news"), shorts("naver-blog"),
                        shorts("threads-voice"), shorts("x-voice"), shorts("comment-guide")]),
    ("instagram-card-news", [shorts("content-common")]),
    ("naver-blog", [shorts("content-common")]),
    # hook-templates is read before every opening line; each content skill links it at its hook step
    ("hook-templates", [shorts("content-common"), shorts("shorts-common"), shorts("instagram-card-news"),
                         shorts("foreign-clip-short"), shorts("top3-compilation-short"), shorts("naver-blog"),
                         shorts("threads-voice"), shorts("x-voice")]),
    # every skill that writes Threads or X copy sends it through that platform's voice skill; the feedback intake names both
    ("threads-voice", [shorts("content-common"), shorts("hook-templates"), shorts("instagram-card-news"),
                       shorts("comment-guide")]),
    ("x-voice", [shorts("content-common"), shorts("hook-templates"), shorts("comment-guide")]),
    # comment rules live once in comment-guide; the skills that write posts point there instead of repeating them
    ("comment-guide", [shorts("content-common"), shorts("threads-voice"), shorts("x-voice"),
                       shorts("instagram-card-news")]),
]

# a manifest slot's fields; anything else is a typo the orchestrator would silently ignore
SLOT_REQUIRED = {"invoke", "env", "notes"}
SLOT_OPTIONAL = {"setup", "reads", "model", "models"}

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
        block = re.search(rf"^{LANG_BLOCK}\n(.*?)(?=^## |\Z)", text, re.M | re.S)
        if pdir.name == "base" and block and len(block.group(1).strip()) > MAX_LANG_BLOCK:
            fail(skill, f"`{LANG_BLOCK}` block is too long (keep under {MAX_LANG_BLOCK}; the full rule is references/output-language.md)")
        check_links(skill, text)
        for ref in sorted(skill.parent.glob("references/*.md")):
            check_links(ref, ref.read_text(encoding="utf-8"))
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
    for ref in re.findall(r"\]\(((?:\.\./)+[^)#\s]+|(?:references|scripts)/[^)#\s]+|[a-z0-9-]+\.md)", text):
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
    # a slot may name a skill of any plugin in this marketplace (content → /gshorts:…)
    plugins = {(load_json(d / ".claude-plugin" / "plugin.json") or {}).get("name"): d
               for d in sorted(ROOT.glob("plugins/*")) if (d / ".claude-plugin" / "plugin.json").is_file()}
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
        if "model" in spec and (not isinstance(spec["model"], str) or not spec["model"] or models is not None):
            fail(path, f"slot {slot}: model must be one model name, and not next to models")
        if not spec.get("notes"):
            fail(path, f"slot {slot}: empty notes")
        if spec.get("invoke") is None and not spec.get("reads"):
            fail(path, f"slot {slot}: invoke null needs reads")
        for field in ("invoke", "setup"):
            cmd = spec.get(field)
            if cmd is None:
                continue
            if field == "invoke" and re.fullmatch(r"<[^<>]+>", cmd):
                continue  # a bare placeholder: the runner's --task is the whole prompt (task slot)
            m = re.match(r"/([a-z0-9-]+):([a-z0-9-]+)", cmd)
            if not m or m.group(1) not in plugins:
                fail(path, f"slot {slot}: {field} {cmd!r} isn't a /<plugin>:<skill> command of {sorted(plugins)}")
                continue
            owner = plugins[m.group(1)]
            if not (owner / "skills" / m.group(2) / "SKILL.md").exists() and not (owner / "commands" / f"{m.group(2)}.md").exists():
                fail(path, f"slot {slot}: {field} names missing skill {m.group(1)}:{m.group(2)}")
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


def check_tracker_free():
    for f in TRACKER_FREE:
        for n, line in enumerate((ROOT / f).read_text(encoding="utf-8").split("\n"), 1):
            m = re.search(TRACKER_NAMES, line, re.I)
            if m:
                fail(f, f"line {n} names a tracker ({m.group(0)}) — say the verb and let the environment file say how (references/environment.md)")


def load_script(rel):
    """A script of this repo as a module (their names have dashes, so they can't be imported)."""
    spec = importlib.util.spec_from_file_location(Path(rel).stem.replace("-", "_"), ROOT / rel)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def check_playbooks():
    """Every playbook work's route table names is one pstack-sync wrote: an upstream rename fails here, not in a run."""
    text = (ROOT / skill("work")).read_text(encoding="utf-8")
    section = re.search(r"^## 1\. Pick one route\n(.*?)(?=^## )", text, re.M | re.S)
    rows = re.findall(r"^\|.*$", section.group(1), re.M) if section else []  # the table's rows, not the prose around it
    names = re.findall(r"`([a-z0-9-]+\.md)`", "\n".join(rows))
    if not names:
        fail(skill("work"), "route table names no playbook (`<name>.md`)")
    for name in names:
        if not (ROOT / PLAYBOOK_DIR / name).is_file():
            fail(skill("work"), f"route table names playbook {name}, which is not in {PLAYBOOK_DIR}/")


def check_read_budget():
    """A PR route's main session doesn't load more instruction text than scripts/read-budget.json allows."""
    for problem in load_script("scripts/read-budget.py").problems():
        fail("scripts/read-budget.json", problem)


def check_pstack():
    """Followed pstack items are what pstack-sync wrote, and no upstream change to a merged skill is left unmerged."""
    sync = load_script(PSTACK_SYNC)
    try:
        for problem in sync.verify(ROOT):
            path, _, msg = problem.partition(": ")
            fail(path, msg)
    except sync.SyncError as e:
        fail(PSTACK_SYNC, str(e))


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
    check_tracker_free()
    check_pstack()
    check_playbooks()
    check_read_budget()
    if base:
        check_version_bumps(base, versions)
    if errors:
        print("\n".join(f"FAIL {e}" for e in errors))
        sys.exit(1)
    print(f"PASS ({len(versions)} plugins)")


if __name__ == "__main__":
    main()
