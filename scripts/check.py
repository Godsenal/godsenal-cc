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
from typing import NamedTuple, Union

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
PREVIEW = "plugins/base/skills/branch-pr/references/preview.md"
SHIP_PREP = "plugins/base/skills/branch-pr/scripts/ship-prep"
SETTLE = "plugins/base/skills/monitor/references/settle.md"
MERGE = "plugins/base/skills/monitor/references/merge.md"
CONFLICTS = "plugins/base/skills/monitor/references/conflicts.md"
COMMENTS = "plugins/base/skills/monitor/references/comments.md"
HELD_REPLIES = "plugins/base/skills/monitor/references/held-replies.md"
PR_STATUS = "plugins/base/skills/monitor/scripts/pr-status"
ORCHESTRATOR = "plugins/base/references/orchestrator.md"
HEADLESS = "plugins/base/references/headless.md"
HARNESS = "plugins/base/references/harness.md"
SESSION_HOOK = "plugins/base/hooks/session-start.md"
FACTORY = "plugins/base/.claude-plugin/factory.json"
POLISH_COMMENTS = "plugins/base/skills/polish/references/comments.md"  # polish's Pass 0: pstack's no-comments, read by path
ADDED_COMMENTS = "plugins/base/skills/polish/scripts/added-comments"
PREMISE = "plugins/base/references/premise.md"
REVIEW_TESTS = "plugins/base/skills/review/references/tests.md"
RUNNER = "scripts/gbase-run"
CONVENTIONS = "plugins/base/references/conventions.md"
ENVIRONMENT = "plugins/base/references/environment.md"
SETUP_ENV = "plugins/base/skills/setup/references/explore-environment.md"
TRACKER_FREE = [skill("work"), skill("go"), BRANCH_PR, skill("monitor"), PR_BODY, LOCAL_MODE, PREVIEW, SHIP_PREP, GO_REVIEW, GO_VERIFY, GO_HIGH,
                GO_DRAFT_MERGE, GO_ORCH, SETTLE, MERGE, CONFLICTS, COMMENTS, HELD_REPLIES, PR_STATUS]
TRACKER_NAMES = r"\b(jira|acli|atlassian|linear|asana|trello|youtrack)\b"
PSTACK_SYNC = "scripts/pstack-sync.py"
PSTACK_DOC = "plugins/base/references/pstack-sync.md"
REFS_WATCH = "scripts/refs-watch.py"
PSTACK_ADAPTER = "plugins/base/references/pstack-adapter.md"
TRIGGERS = "scripts/triggers.py"
RUNNER_DOC = "plugins/base/references/runner.md"  # the runner's usage and result.json, split out of orchestrator.md


class Contract(NamedTuple):
    name: str
    why: str
    checks: list[Union[tuple[str, list[str]], tuple[str, list[str], str]]]  # Union, not |: stock macOS python3 is 3.9


CONTRACTS = [
    Contract("compat-verdict", "branch-pr parses compat-check's verdict tokens", [
        ("⚠️ requires ordered rollout", [skill("compat-check"), BRANCH_PR]),
        ("- `✅ no special deploy ordering needed`", [skill("compat-check")],
         "compat-check's output template itself, not just prose that mentions the tokens"),
        ("- `⚠️ requires ordered rollout`", [skill("compat-check")],
         "compat-check's output template itself, not just prose that mentions the tokens"),
    ]),
    Contract("review-under-go", "go and monitor start review with these words, and review recognizes its mode by the same wording", [
        ("start at stage 2", [GO_REVIEW, skill("review")]),
        ("defer, don't ask", [GO_REVIEW, skill("review"), skill("monitor")]),
        ("one skeptic for low/medium", [skill("go"), GO_REVIEW, GO_ORCH, skill("review")]),
    ]),
    Contract("skills-in-subagents",
             "polish, review, compat-check, and unslop run in subagents so their bodies stay out of the main session, and a subagent can't ask", [
        ('skill(skill: "gbase:polish"', [skill("go")]),
        (r'skill(skill: \"gbase:review\"', [GO_REVIEW],
         "review.md writes the call inside a quoted prompt, so the backslash is part of the token"),
        ('skill(skill: "gbase:review"', [skill("monitor")]),
        ('skill(skill: "gbase:compat-check"', [BRANCH_PR]),
        ('skill(skill: "gbase:unslop"', [BRANCH_PR, skill("work")]),
        ("awaiting confirm", [skill("go"), skill("polish"), COMMENTS, CONFLICTS],
         "every polish launch says what a subagent that can't ask does"),
        ("subagent that can't ask", [skill("compat-check")]),
    ]),
    Contract("agent-env-probe", "go reads the orchestrator's AGENT_* variables with this one command", [
        ("printenv | grep '^agent_'", [skill("go"), GO_ORCH],
         "in go's Step 1 prose, runnable as written (a table cell needs the pipe escaped)"),
    ]),
    Contract("go-branch-references", "go's body names the reference each branch reads; the branch's tokens live in that file, not in the body", [
        ("references/review.md", [skill("go")]),
        ("references/verify.md", [skill("go")]),
        ("references/draft-merge.md", [skill("go")]),
        ("references/orchestrated.md", [skill("go")]),
    ]),
    Contract("high-verification",
             "high adds its verification in one file: an agent that didn't write the code runs the behavior check, and an open check holds the merge", [
        ("references/high.md", [skill("go")]),
        ("high.md", [GO_VERIFY]),
        ("risk line", [GO_HIGH, CONFLICTS], "monitor learns the tier from the PR body branch-pr wrote, not from a flag"),
        ("statechart", [GO_HIGH]),
        ("create-formal-verification-skill", [GO_HIGH]),
    ]),
    Contract("behavior-skip-unverified",
             "a skipped behavior check is unverified, not passed: a (확인) item in the PR, `open` in the evidence file, `unverified` in result.json", [
        ("behavior: skip", [skill("work"), GO_VERIFY, GO_HIGH, BRANCH_PR, PR_BODY, SHIP_PREP, ORCHESTRATOR]),
        ("(확인)", [GO_VERIFY, PR_BODY, SHIP_PREP, ORCHESTRATOR]),
        ('== "open"', [SHIP_PREP, RUNNER]),
        ("unverified", [GO_VERIFY, SHIP_PREP, RUNNER, RUNNER_DOC, ORCHESTRATOR]),
    ]),
    Contract("patch-id-reverify",
             "after a rebase or base merge on a high PR, pr-status compares patch ids and its next: line says whether to re-verify", [
        ("git patch-id", [PR_STATUS, CONFLICTS, ORCHESTRATOR]),
        ("pr-status script> patch", [CONFLICTS]),
        ("nothing to re-verify", [PR_STATUS, CONFLICTS]),
        ("one verifier", [PR_STATUS, CONFLICTS]),
    ]),
    Contract("review-proven-marks",
             "review marks a high finding a run proved, inside the finding cell, and keeps one no run could reach; the runner reads the table's columns", [
        ("references/proven.md", [skill("review")]),
        ("실행으로 확인됨", [REVIEW_PROVEN]),
        ("실행 증거 없음", [REVIEW_PROVEN]),
    ]),
    Contract("work-behavior-lines", "work hands go its surface verification so go doesn't run the behavior check twice", [
        ("`behavior:`", [skill("work"), skill("go"), GO_VERIFY]),
    ]),
    Contract("monitor-flags", "go calls monitor with these flags, and work adds --merge only when asked; monitor reads them by name", [
        ("--no-review", [skill("go"), skill("monitor")]),
        ("--draft", [skill("go"), GO_DRAFT_MERGE, skill("monitor")]),
        ("--merge", [skill("work"), skill("go"), GO_DRAFT_MERGE, GO_ORCH, skill("monitor")]),
        ("verified-locally", [GO_DRAFT_MERGE, SETTLE, MERGE, PR_STATUS],
         "go passes it with --merge when its checks passed in the run, and monitor hands it to pr-status's merge gate"),
    ]),
    Contract("verify-block", "setup writes the gbase:verify block in the target repo's CLAUDE.md that go's verification gate reads", [
        ("gbase:verify", [skill("setup"), skill("go"), GO_VERIFY]),
    ]),
    Contract("go-to-branch-pr-lines",
             "go hands branch-pr its risk tier, check results, and deferred findings as these lines; deferred findings land in the PR body's Review focus", [
        ("verification:", [skill("go"), BRANCH_PR]),
        ("risk:", [skill("go"), BRANCH_PR]),
        ("deferred:", [skill("go"), BRANCH_PR]),
        ("## review focus", [skill("go"), GO_DRAFT_MERGE, BRANCH_PR, PR_BODY, SHIP_PREP, ORCHESTRATOR]),
    ]),
    Contract("pause-commit-marker",
             "pause leaves a wip: commit whose body starts with Intent:, the marker pickup, go, and branch-pr use to recognize it before it is soft-reset into real commits", [
        ("intent:", [skill("pause"), skill("pickup"), skill("go"), BRANCH_PR]),
        ("git reset --soft", [BRANCH_PR]),
        ('"wip:"', [SHIP_PREP], "ship-prep does the reset; its marker is the same wip: + Intent: pair pause writes"),
    ]),
    Contract("backup-ref", "ship-prep backs the tree up under this ref on every branch-pr run, and the runner prunes old ones by the same prefix", [
        ("refs/gbase/backup/", [BRANCH_PR, SHIP_PREP, RUNNER]),
    ]),
    Contract("verify-skills", "create-verify generates .claude/skills/verify-* that go runs for touched features; go also runs pstack's .claude/skills/verify/", [
        (".claude/skills/verify-", [skill("create-verify"), GO_VERIFY]),
        (".claude/skills/verify/", [skill("create-verify"), GO_VERIFY, skill("setup")]),
    ]),
    Contract("orchestrator-ship",
             "when the orchestrator owns shipping, go passes branch-pr the owner and a PR body file, and both print the ship: / PR 본문 초안: lines the caller greps", [
        ("ship-owner: orchestrator", [GO_ORCH, BRANCH_PR]),
        ("pr-body-file:", [GO_ORCH, BRANCH_PR]),
        ("ship: local", [LOCAL_MODE, ORCHESTRATOR, SETTLE]),
        ("ship: skip —", [HEADLESS, ORCHESTRATOR], "a shipping step the caller put out of scope, not a decision"),
        ("pr 본문 초안:", [GO_ORCH, LOCAL_MODE, ORCHESTRATOR, RUNNER, SETTLE]),
    ]),
    Contract("pr-preview",
             "where the owner reads a change before its PR, ship-prep finds the setting, records the commit that was shown, and refuses to push "
             "another one; branch-pr writes the preview and asks, go resumes at a recorded commit, and the runner takes the stop for the run's end", [
        ("before the pr: preview", [ENVIRONMENT, CONVENTIONS, SETUP_ENV, ORCHESTRATOR, SHIP_PREP]),
        ("## shipping", [ENVIRONMENT, SETUP_ENV]),
        ("references/preview.md", [BRANCH_PR, ENVIRONMENT]),
        ("`preview:` line", [skill("go"), BRANCH_PR, PREVIEW]),
        ("preview: on —", [SHIP_PREP], "start's line for the setting; preview.md routes on the three states by name"),
        ("`preview: on`", [PREVIEW]),
        ("preview: prepared", [SHIP_PREP, PREVIEW]),
        ("preview: changed", [SHIP_PREP, PREVIEW]),
        ("ship-prep preview", [SHIP_PREP, PREVIEW]),
        ("--write", [SHIP_PREP, PREVIEW], "the script saves the preview file, so no tool permission decides whether it exists"),
        ("--reviewed", [SHIP_PREP, PREVIEW], "only a commit go reviewed is recorded as one a later go may skip its review for"),
        ('`"reviewed": true`', [skill("go")], "the key ship-prep writes with json.dumps, read by go's Step 1"),
        ('"reviewed": "--reviewed" in args', [SHIP_PREP]),
        ("`--preview`", [skill("go"), GO_DRAFT_MERGE, BRANCH_PR, PREVIEW], "a one-off request travels go → branch-pr's args → preview.md"),
        ("--no-preview", [SHIP_PREP, PREVIEW]),
        ('gbase/preview-$(git rev-parse head).json', [skill("go")],
         "go's Step 1 reads the state file by the commit's sha, so only the commit that was shown skips the review"),
        ('f"preview-{head}.json"', [SHIP_PREP], "the name go's Step 1 reads"),
        ('print(f"ship: local ', [SHIP_PREP], "the stop reports the same lines local mode does"),
        ("ship: local", [PREVIEW]),
        ("pr 본문 초안:", [PREVIEW, SHIP_PREP]),
        ("여기서 멈춤", [PREVIEW]),
        ("→ 열지 않음", [PREVIEW], "headless: the stop is a 결정 필요: line, not a recommendation applied"),
        ("`preview: <absolute path>`", [ORCHESTRATOR]),
        ("preview_file", [RUNNER, RUNNER_DOC]),
        ("and preview.search(text)", [RUNNER], "unshipped(): a run that stopped at the preview is not resumed to push"),
    ]),
    Contract("held-replies",
             "where the user posts their own replies to reviewers, pr-status finds the setting, tells monitor to post nothing, and remembers "
             "which comments already have a draft; monitor drafts and asks, and the runner takes unpushed comment fixes for the run's end", [
        ("review replies: draft", [ENVIRONMENT, CONVENTIONS, SETUP_ENV, ORCHESTRATOR, RUNNER_DOC, HELD_REPLIES, GO_DRAFT_MERGE]),
        ('review replies[`*_]*', [PR_STATUS], "the pattern that reads the environment file's line"),
        ("`replies: draft` line", [skill("monitor"), COMMENTS, HELD_REPLIES], "the line that sends monitor to held-replies.md"),
        ('f"replies: draft — ', [PR_STATUS]),
        ("references/held-replies.md", [skill("monitor"), ENVIRONMENT, PR_STATUS]),
        ("--hold-replies", [skill("monitor"), skill("go"), GO_DRAFT_MERGE, HELD_REPLIES, ENVIRONMENT, PR_STATUS],
         "a one-off request travels go → monitor's args → pr-status"),
        ("--post-replies", [skill("monitor"), skill("go"), GO_DRAFT_MERGE, HELD_REPLIES, ENVIRONMENT, PR_STATUS], "the request wins over the file"),
        ("pr-status\" drafted", [HELD_REPLIES], "the command that records the drafts"),
        ('args[0] == "drafted"', [PR_STATUS]),
        ("댓글 | 판단 | 수정 커밋 | 답글 초안", [HELD_REPLIES, PR_STATUS], "the table the user reads is the one the script prints"),
        ("`held replies`", [HELD_REPLIES]),
        ('f"held replies: ', [PR_STATUS]),
        ("new comment since a draft", [HELD_REPLIES, PR_STATUS]),
        ("`next: post`", [HELD_REPLIES]),
        ('f"post — ', [PR_STATUS]),
        ('f"held — ', [PR_STATUS], "a watch with nothing left but held drafts has to end"),
        ("(답글 초안)", [HELD_REPLIES, PR_STATUS, ORCHESTRATOR], "a held comment still needs a person: the settle verdict says so"),
        ("`reply drafts: <path>`", [HELD_REPLIES]),
        ('f"reply drafts: {', [PR_STATUS]),
        ("`reply drafts: <absolute path>`", [ORCHESTRATOR]),
        ("reply_drafts_file", [RUNNER, RUNNER_DOC]),
        ("fixes_wait_on_held_replies = REPLY_DRAFTS.search(text)", [RUNNER], "unshipped(): a run whose comment fixes wait unpushed is not resumed to push them"),
        ("→ 올리지 않음", [HELD_REPLIES], "headless: holding is a 결정 필요: line, and nothing is posted on a recommendation"),
        ("wait --handled", [HELD_REPLIES, SETTLE], "the headless path reuses settle.md's local-commit rules instead of restating them"),
        ("`agent_ship_owner=orchestrator` section", [HELD_REPLIES]),
        ("## `agent_ship_owner=orchestrator`", [SETTLE]),
        ("what the team sees", [SETUP_ENV]),
    ]),
    Contract("pr-url-line", "agent-owned runs: branch-pr prints the PR URL, go carries it up, the runner parses it into pr_url", [
        ("`pr: <url>`", [skill("go"), GO_ORCH, BRANCH_PR, ORCHESTRATOR, RUNNER, FACTORY]),
        ('print(f"pr: {', [SHIP_PREP], "the script prints the line the skill promises"),
        ("pr_url", [RUNNER_DOC, RUNNER]),
    ]),
    Contract("conventions", "conventions.md holds the one setting > convention > default order; the runner reads its branch prefix key", [
        ("gbase.branchprefix", [CONVENTIONS, RUNNER_DOC, RUNNER]),
        ("references/conventions.md", [BRANCH_PR, MERGE]),
    ]),
    Contract("environment-file",
             "the user's environment file says how a ticket is read and which write-backs are on; skills only say the verb, and ship-prep's environment: line sends branch-pr to its Shipping it section", [
        ("gbase.conventions", [CONVENTIONS, ENVIRONMENT, skill("work"), SHIP_PREP, SETUP_ENV]),
        ("references/environment.md", [skill("work"), skill("setup"), SETUP_ENV]),
        ("(environment.md)", [CONVENTIONS]),
        ("references/explore-environment.md", [skill("setup")]),
        ("`environment:` line", [ENVIRONMENT]),
        ('"environment: ', [SHIP_PREP]),
        ("shipping it", [ENVIRONMENT, SHIP_PREP]),
        ("## write-back", [ENVIRONMENT]),
        ('"fetch the ticket"', [ENVIRONMENT]),
        ("link the pr on the ticket", [ENVIRONMENT, SETUP_ENV]),
        ("ticket: <key> → not read", [ENVIRONMENT]),
        ("is not permission", [ENVIRONMENT]),
        ("draft only", [SETUP_ENV]),
    ]),
    Contract("settle-line", "monitor --until-settled ends with a settle: line that pr-status prints and the orchestrator reads", [
        ("--until-settled", [skill("monitor"), SETTLE, GO_ORCH, ORCHESTRATOR]),
        ("settle: 수렴", [SETTLE, PR_STATUS, ORCHESTRATOR]),
        ("settle: 미확정", [SETTLE, PR_STATUS, ORCHESTRATOR]),
        ("settle: 사람 필요", [SETTLE, PR_STATUS, ORCHESTRATOR]),
    ]),
    Contract("pr-status-lines", "monitor acts on pr-status's output lines and flags: a line or flag the skill or a reference names is one the script prints or takes", [
        ('"conflict — ', [PR_STATUS]),
        ("| `conflict` |", [skill("monitor")]),
        ('"comments — ', [PR_STATUS]),
        ("| `comments` |", [skill("monitor")]),
        ('"ci — ', [PR_STATUS]),
        ("| `ci` |", [skill("monitor")]),
        ('"notes — ', [PR_STATUS]),
        ("`notes`", [skill("monitor")], "no row of its own: the script's line says what to do with a bot's comment"),
        ('"settled — ', [PR_STATUS]),
        ("| `settled` |", [skill("monitor")]),
        ('"limit — ', [PR_STATUS]),
        ("`next: limit`", [SETTLE]),
        ('"give up — ', [PR_STATUS]),
        ("`give up`", [skill("monitor"), SETTLE]),
        ('"unstarted — ', [PR_STATUS]),
        ("`unstarted`", [skill("monitor")]),
        ("merge: gate passed", [PR_STATUS, MERGE]),
        ("merge: not now", [PR_STATUS, MERGE]),
        ("merge: retarget stacked pr first", [PR_STATUS, MERGE]),
        ("--handled", [PR_STATUS, SETTLE]),
    ]),
    Contract("ship-prep-lines", "branch-pr acts on ship-prep's output lines and flags: a line the skill or a reference names is one the script prints", [
        ('"ask: ', [SHIP_PREP]),
        ("`ask:` lines", [BRANCH_PR]),
        ("branch plan:", [SHIP_PREP, BRANCH_PR]),
        ("--partial", [SHIP_PREP, BRANCH_PR]),
        ("--remote", [SHIP_PREP, BRANCH_PR]),
        ("ship-prep start --local", [LOCAL_MODE]),
        ("ship-prep check", [LOCAL_MODE]),
        ("ship-prep assets", [PR_BODY, LOCAL_MODE]),
        ("compat: run", [BRANCH_PR, SHIP_PREP]),
        ("compat: skip", [BRANCH_PR, SHIP_PREP]),
    ]),
    Contract("split-out-branches",
             "monitor's and branch-pr's bodies name the script and the reference each branch reads, and pr-status's next: lines name the same reference; "
             "the branch's tokens live in that file, not in the body", [
        ("scripts/pr-status", [skill("monitor")]),
        ("references/settle.md", [skill("monitor")]),
        ("references/merge.md", [skill("monitor")]),
        ("references/comments.md", [skill("monitor"), PR_STATUS]),
        ("references/conflicts.md", [skill("monitor"), PR_STATUS]),
        ("scripts/ship-prep", [BRANCH_PR]),
        ("references/pr-body.md", [BRANCH_PR]),
        ("references/local-mode.md", [BRANCH_PR]),
    ]),
    Contract("decision-line", "headless runs report a question as a 결정 필요: line, and the runner splits it on these keys into recommend / options / human", [
        ("결정 필요:", [HEADLESS, ORCHESTRATOR, RUNNER]),
        ("(추천:", [HEADLESS, RUNNER]),
        ("다른 선택지", [HEADLESS, RUNNER]),
        ("사람이 할 일", [HEADLESS, RUNNER]),
    ]),
    Contract("no-wakeups", "headless forbids wakeups in prose; the runner enforces it by denying the tools", [
        ("schedulewakeup,croncreate", [HEADLESS, RUNNER_DOC, RUNNER]),
    ]),
    Contract("bare-task-forbid-list",
             "bare task runs load no skill: the runner (and a bot's direct template, via harness.md) carries the forbid list", [
        ("대표자·본인 확인 체크", [HEADLESS, ORCHESTRATOR, RUNNER, HARNESS]),
    ]),
    Contract("settle-local-fixes", "settle keeps fixes local and pushes only when the agent owns shipping", [
        ("agent_ship_owner=orchestrator", [GO_ORCH, skill("monitor"), SETTLE, skill("review"), ORCHESTRATOR]),
        ("푸시 대기:", [SETTLE, ORCHESTRATOR]),
    ]),
    Contract("evidence-file",
             "go and reproduce write the evidence file format; it records what a check ran on, and a `differs:` input becomes a Review focus item", [
        ("agent_evidence_file", [GO_ORCH, skill("reproduce"), SETTLE, ORCHESTRATOR]),
        ("`input`", [ORCHESTRATOR, GO_VERIFY, GO_ORCH, skill("reproduce")]),
        ("differs:", [ORCHESTRATOR, GO_VERIFY, skill("reproduce"), BRANCH_PR, PR_BODY]),
        ("input differs from report", [ORCHESTRATOR, skill("reproduce")]),
    ]),
    Contract("unreviewed-conflict-resolution",
             "a conflict resolution that combined both sides and got no review is pushed only with this evidence line", [
        ("conflict resolution unreviewed", [CONFLICTS]),
    ]),
    Contract("bug-fix-reproduce", "bug-fix starts with gbase:reproduce, which only writes the failing check; the fix stays in bug-fix", [
        ("gbase:reproduce", [skill("bug-fix"), skill("reproduce")]),
    ]),
    Contract("session-hook-routing",
             "the session hook routes to work (and plan) by the same criteria as work's description, and names the agent types work dispatches", [
        ("`gbase:work`", [SESSION_HOOK]),
        ("gbase:scout", [skill("work"), SESSION_HOOK]),
        ("gbase:worker", [skill("work"), SESSION_HOOK]),
        ("changes a signature other files call", [skill("work"), SESSION_HOOK]),
        ("a diagnosis from a trace or profile", [skill("work"), SESSION_HOOK]),
        ("spans several prs", [skill("work"), SESSION_HOOK]),
        ("`gbase:plan`", [SESSION_HOOK, skill("work")]),
    ]),
    Contract("work-poteto-mode",
             "work is poteto-mode inside gbase: it routes to pstack's playbooks and reads their Cursor names through playbooks.md", [
        ("../poteto-mode/playbooks/", [skill("work")]),
        ("references/playbooks.md", [skill("work")]),
        ("pstack-adapter.md", [WORK_PLAYBOOKS]),
        ("benchmark-checklist", [skill("work")]),
        ("root cause before smallest", [skill("work")]),
        ("references/correction.md", [skill("work")]),
    ]),
    Contract("polish-comment-pass",
             "polish's Pass 0 is pstack's no-comments: the script decides whether it runs, go passes the tier and carries what stays open", [
        ("next: comment pass", [ADDED_COMMENTS, skill("polish"), POLISH_COMMENTS]),
        ("next: skip", [ADDED_COMMENTS, skill("polish")]),
        ("next: read the diff yourself", [ADDED_COMMENTS, skill("polish")]),
        ("scripts/added-comments", [skill("polish")]),
        ("references/comments.md", [skill("polish"), ADDED_COMMENTS]),
        ("../../no-comments/skill.md", [POLISH_COMMENTS]),
        ("gbase:comment-sicko", [POLISH_COMMENTS]),
        ("risk: <tier>", [skill("go")]),
        ("stays deleted", [skill("go")], "go's main session once restored a constraint comment polish had deleted"),
        ("`comments:`", [skill("go"), GO_VERIFY, GO_DRAFT_MERGE, POLISH_COMMENTS]),
        ("comments: skip —", [ADDED_COMMENTS, skill("polish")]),
        ("don't encode", [POLISH_COMMENTS]),
        ('"skills/polish/references/comments.md"', ["scripts/pstack/lock.json"]),
    ]),
    Contract("premise-after-two-fixes",
             "a check still failing after two fixes: verify.md, monitor's ci row, and pr-status's ci line all point at premise.md, which writes the premise, makes one observation, and stops with no third fix", [
        ("../../references/premise.md", [GO_VERIFY, skill("monitor"), PR_STATUS]),
        ("principle-attack-the-premise/skill.md", [PREMISE]),
        ("write the premise", [PREMISE]),
        ("one observation", [PREMISE]),
        ("no third fix", [PREMISE, PR_STATUS]),
        ("a third fix included", [GO_VERIFY]),
        ("결정 필요: <체크>가 수정 두 번 뒤에도 실패", [PREMISE]),
        ('"references/premise.md"', ["scripts/pstack/lock.json"]),
    ]),
    Contract("review-test-files",
             "a test file the target adds or changes: review judges each test against the two imagined edits itself, and a test that fails one is never auto-fixed", [
        ("references/tests.md", [skill("review")]),
        ("principle-test-behavior-not-implementation/skill.md", [REVIEW_TESTS]),
        ("break the behavior", [REVIEW_TESTS]),
        ("change the internals", [REVIEW_TESTS]),
        ("no agent is launched", [REVIEW_TESTS]),
        ("never auto-fixed", [REVIEW_TESTS]),
        ("no skeptic is launched for these alone", [REVIEW_TESTS]),
        ('"skills/review/references/tests.md"', ["scripts/pstack/lock.json"]),
    ]),
    Contract("failed-check-suspects-the-look",
             "a check that fails: verify.md suspects how it looked before the code, and its behavior check is a command that reruns the same comparison", [
        ("suspect how you looked", [GO_VERIFY]),
        ("reruns the same comparison", [GO_VERIFY]),
    ]),
    Contract("explain-the-number", "a number to measure: work's route sentence names this leaf ahead of benchmark-checklist", [
        ("../principle-explain-the-number/skill.md", [skill("work")]),
    ]),
    Contract("lessons-line", "content runs report lessons instead of editing the harness; the runner hands them to a work run", [
        ("교훈:", [shorts("content-common"), shorts("shorts-common"), skill("design-taste"), ORCHESTRATOR, RUNNER, FACTORY]),
    ]),
    Contract("design-taste",
             "mockup and gapp's design load the user's taste rules before drawing; work loads them before screen work, and its workers do too (they don't inherit loaded skills)", [
        ("gbase:design-taste", [skill("mockup"), "plugins/app/skills/design/SKILL.md", skill("work"),
                                "plugins/base/skills/work/references/workers.md", "plugins/base/agents/worker.md"]),
    ]),
    Contract("runner-flags", "runner.md documents the flags gbase-run parses", [
        ("--exclusive", [RUNNER_DOC, RUNNER]),
        ("--max-turns", [RUNNER_DOC, RUNNER]),
        ("--max-budget-usd", [RUNNER_DOC, RUNNER]),
    ]),
    Contract("followups-line",
             "work's size gate reports the slices it left; the runner reads them into followups, and asks a capped run for them", [
        ("남은 작업:", [skill("work"), ORCHESTRATOR, RUNNER, RUNNER_DOC]),
    ]),
    Contract("plan-report", "plan reports its file and slices; the runner reads them into plan_file and followups", [
        ("`plan: <absolute path>`", [skill("plan"), ORCHESTRATOR]),
        ("plan_file", [RUNNER_DOC, RUNNER]),
    ]),
    Contract("runner-start",
             "bots start background runs with this one line, not a long nohup claude -p a permission classifier blocks", [
        ("gbase-run start", [RUNNER_DOC, RUNNER, FACTORY, "README.md"]),
    ]),
    Contract("settle-rebase-exception", "settle's one rebase exception, so it stays one rule and not an open door", [
        ("explicitly asks to rebase", [SETTLE, ORCHESTRATOR, FACTORY, "README.md"]),
    ]),
    Contract("mockup-report", "the runner reads mockup's report lines into result.json", [
        ("mockup url:", [skill("mockup"), RUNNER, ORCHESTRATOR]),
        ("mockup shots:", [skill("mockup"), RUNNER, ORCHESTRATOR]),
    ]),
    Contract("mockup-explicit-only",
             "mockup stays out of work/go runs (company repos included): explicit /gbase:mockup or --slot mockup only", [
        ("disable-model-invocation: true", [skill("mockup")]),
    ]),
    Contract("review2-report-only", "review2 runs review twice on one tree; report only keeps the two sessions from editing", [
        ("report only", [skill("review"), FACTORY]),
    ]),
    Contract("review-table", "the runner merges review2 by parsing review's report table", [
        ("# | severity | file:line | finding | action", [skill("review"), RUNNER]),
    ]),
    Contract("pstack-sync",
             "the daily routine parses --check's fields; every followed skill links the adapter the script names, and the lock's used_by names the gbase files to recheck", [
        ("used_by", [PSTACK_SYNC, PSTACK_DOC]),
        ("skills_changed", [PSTACK_SYNC, PSTACK_DOC]),
        ("custom_changed", [PSTACK_SYNC, PSTACK_DOC]),
        ("new_upstream", [PSTACK_SYNC, PSTACK_DOC]),
        ("scripts_changed", [PSTACK_SYNC, PSTACK_DOC]),
        ("references/pstack-adapter.md", [PSTACK_SYNC, PSTACK_DOC]),
    ]),
    Contract("refs-watch", "a routine that runs refs-watch --check parses its per-repo fields as the doc names them", [
        ("new_skills", [REFS_WATCH, PSTACK_DOC]),
        ("removed_skills", [REFS_WATCH, PSTACK_DOC]),
        ("changed_skills", [REFS_WATCH, PSTACK_DOC]),
        ("scripts/refs/lock.json", [REFS_WATCH, PSTACK_DOC]),
    ]),
    Contract("pstack-adapter",
             "the adapter sends every shipping step of a pstack playbook through go, and questions through headless.md", [
        ("gbase:go", [PSTACK_ADAPTER, WORK_PLAYBOOKS]),
        ("headless.md", [PSTACK_ADAPTER]),
    ]),
    Contract("gshorts-shorts-common",
             "gshorts format skills defer every-video rules to shorts-common; its feedback intake names the format skills", [
        ("shorts-common", [shorts("foreign-clip-short"), shorts("top3-compilation-short")]),
        ("foreign-clip-short", [shorts("shorts-common"), shorts("top3-compilation-short")]),
        ("top3-compilation-short", [shorts("shorts-common")]),
    ]),
    Contract("gshorts-content-common",
             "content-common holds rules for every piece of content; shorts-common, instagram-card-news, naver-blog, threads-voice, x-voice, and comment-guide defer to it", [
        ("content-common", [shorts("shorts-common"), shorts("instagram-card-news"), shorts("naver-blog"),
                            shorts("threads-voice"), shorts("x-voice"), shorts("comment-guide")]),
        ("instagram-card-news", [shorts("content-common")]),
        ("naver-blog", [shorts("content-common")]),
    ]),
    Contract("gshorts-hook-templates", "hook-templates is read before every opening line; each content skill links it at its hook step", [
        ("hook-templates", [shorts("content-common"), shorts("shorts-common"), shorts("instagram-card-news"),
                             shorts("foreign-clip-short"), shorts("top3-compilation-short"), shorts("naver-blog"),
                             shorts("threads-voice"), shorts("x-voice")]),
    ]),
    Contract("gshorts-voice",
             "every skill that writes Threads or X copy sends it through that platform's voice skill; the feedback intake names both", [
        ("threads-voice", [shorts("content-common"), shorts("hook-templates"), shorts("instagram-card-news"),
                           shorts("comment-guide")]),
        ("x-voice", [shorts("content-common"), shorts("hook-templates"), shorts("comment-guide")]),
    ]),
    Contract("gshorts-comment-guide",
             "comment rules live once in comment-guide; the skills that write posts point there instead of repeating them", [
        ("comment-guide", [shorts("content-common"), shorts("threads-voice"), shorts("x-voice"),
                           shorts("instagram-card-news")]),
    ]),
    Contract("trigger-check",
             "check.py prints triggers.py's rank1 line on every run so a baseline can read the ratio from its output; a miss is fixed in the description and a floor only goes up", [
        ("triggers: rank1 {hits}/{total} ({pct}%)", [TRIGGERS]),
        ("triggers: rank1 n/m (p%)", ["CLAUDE.md", "plugins/base/evals/README.md"]),
        ("fix its description", [TRIGGERS]),
        ("only go up", ["plugins/base/evals/triggers.json", TRIGGERS]),
    ]),
    Contract("trigger-holdout",
             "triggers.json splits each skill's prompts into train (for tuning a description) and test (held out); only test is judged, so the rank1 line says how a description does on prompts it wasn't tuned on", [
        ('"train"', ["plugins/base/evals/triggers.json"]),
        ('"test"', ["plugins/base/evals/triggers.json"]),
        ("held-out test", [TRIGGERS, "CLAUDE.md", "plugins/base/evals/README.md"]),
        ("in both train and test", [TRIGGERS]),
    ]),
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
    for contract in CONTRACTS:
        for token, files, *note in contract.checks:
            why = contract.why + "".join(f" ({n})" for n in note)
            for f in files:
                path = ROOT / f
                if not path.exists():
                    fail(f, f"contract file missing (token {token!r}) — {contract.name}: {why}")
                    continue
                if f not in texts:
                    texts[f] = path.read_text(encoding="utf-8").lower()
                if token.lower() not in texts[f]:
                    fail(f, f"contract token {token!r} missing — {contract.name}: {why} — update both sides: {', '.join(files)}")


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


def check_triggers():
    triggers = load_script(TRIGGERS)
    cases = load_json(triggers.CASES)
    if not cases:
        return
    try:
        line, found = triggers.problems(cases, triggers.listing(frontmatter, ROOT))
    except (KeyError, TypeError, AttributeError) as e:
        fail(triggers.CASES, f"malformed — missing or wrong-typed field {e}")
        return
    except ValueError as e:
        fail(TRIGGERS, str(e))
        return
    for problem in found:
        fail("plugins/base/evals/triggers.json", problem)
    print(line)


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
    check_triggers()
    if base:
        check_version_bumps(base, versions)
    if errors:
        print("\n".join(f"FAIL {e}" for e in errors))
        sys.exit(1)
    print(f"PASS ({len(versions)} plugins)")


if __name__ == "__main__":
    main()
