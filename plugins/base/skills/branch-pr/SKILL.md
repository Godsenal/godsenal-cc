---
name: branch-pr
description: "Takes the current changes to an open pull request without step-by-step confirmation: unwraps pause commits, backs up the tree, picks the branch and groups logical commits by the repo's conventions, writes a PR body whose Review focus section says what a person must judge, pushes, and opens the PR. Use when the user asks to open a PR or to commit and push the current work as one, or runs /gbase:branch-pr; also the PR step of gbase:go."
allowed-tools: Bash Read Glob Grep AskUserQuestion Skill
---

# /gbase:branch-pr

Takes the current changes to an open PR: branch, logical commits, push, PR body. Invoking it is the go-ahead for all of that; decide the branch name, the grouping, and the body yourself and report them as you go. It stops only for an `ask:` line from the script below.

## 출력 언어

사용자에게 보이는 글은 **한국어**로 쓰고, 코드·명령·상태 라벨·커밋·브랜치는 레포 관례를 따른다. PR 제목·본문은 기본 한국어(섹션 제목은 영어)이고 레포가 다른 언어로 써 왔으면 그 언어다. 세부: [output-language.md](../../references/output-language.md).

## Safety

Never `git reset --hard`, `git checkout .`, `git clean -f`, `git stash drop`, or `git push --force` (`--force-with-lease` is fine for a legitimate rebase). On any error stop, print `git status`, and give the restore command from the script's `backup:` line.

## Steps

The mechanical parts are one script, `ship-prep` (`scripts/ship-prep` in this skill's directory).

**1. Start.** Args that begin with `Ship-owner: orchestrator; PR-body-file: <path>` mean another program pushes and opens the PR: read [local-mode.md](references/local-mode.md) and add `--local`.

```bash
"${CLAUDE_SKILL_DIR}/scripts/ship-prep" start
```

It unwraps unpushed `gbase:pause` commits (`wip:` subject and an `Intent:` body, via `git reset --soft`; their notes feed the PR's Why) and backs the tree up under `refs/gbase/backup/`. Exit 3 means nothing to ship: say so and stop.

- **`ask:` lines** are questions: a secret in the diff (never commit it), a branch with its own history and no PR, a missing or ambiguous remote. Three more are yours to notice: a secret-looking value the script didn't flag (it only knows common shapes), WIP clearly unrelated to the change, and changes that are clearly separate features (one PR or several). Under `AGENT_HEADLESS=1` (check `printenv AGENT_HEADLESS` before asking) nothing is asked: follow [headless.md](../../references/headless.md). A secret is left out and recorded (then `open --partial`).
- **Read every file on the `conventions` line** before naming anything. The repo's settings, then the user's conventions file, then history, then the gbase default decide the branch name, commit format, PR title, ticket reference, labels, and draft state: [conventions.md](../../references/conventions.md).

**2. Branch and commits.** Follow the `branch plan:` line (a new branch only when it says so; gbase default `feat/` `fix/` `refactor/` `docs/` `chore/` + slug). Group the files into logical commits (by layer or feature), each with the repo's commit format and the attribution trailer the session specifies.

**3. Compat and risk.** On `compat: run`, call `Skill(skill: "gbase:compat-check", args: "<the range on that line>")`, even for a change that looks additive: it is the PR's only deploy-order review. `⚠️ Requires ordered rollout` → its `## Rollout / Deploy order` block goes into the body and its one-line summary to the user. `✅`, or `compat: skip` → no section, nothing said.

Risk, unless the caller passed a `Risk:` line (the tier is set from the change, not the author):

- `high` — touches a path `REVIEW.md` marks always-high (without one: auth, payments/billing, migrations, CI/release workflows, app config like `app.json`/`eas.json`/`Info.plist`), or compat-check returned ⚠️
- `low` — docs, copy, tests, or an additive change behind a flag, and nothing above
- `medium` — everything else

**4. Draft the PR** in a file (`$(git rev-parse --absolute-git-dir)/gbase/pr-body.md`, or the caller's `PR-body-file`): the title on line 1, an empty line 2, the body from line 3. The repo's PR template, when it has one, is the body, with `Review focus` (right under its first section) and `Evidence` added if it lacks them. Otherwise:

```markdown
## Why
<exactly one sentence: the problem, and what becomes possible once this ships>

## Review focus
> [!NOTE]
> **사람이 판단할 곳 없음.** <why the checks and the Evidence cover it>

**위험도** <low / medium / high> (<the path or hazard that set it>) · <two-way / one-way> · <how to undo>

## Change outline
<one numbered `###` heading per concern, at most four; under each a small table or diff and at most three one-sentence bullets saying why. Not a per-file changelog>

## Evidence
<before → after first; then the caller's `Verification:` lines, one `- [x]` each with what was observed>

🤖 Generated with [Claude Code](https://claude.com/claude-code)
```

The body before `## Change outline` fits on one screen; every cell and bullet is a sentence someone outside this session understands.

**Read [pr-body.md](references/pr-body.md) before drafting when any of these holds**; a `low` change with none of them uses the skeleton as it is:

- the risk is `medium` or `high`, or the change is one-way (something outlives a revert)
- the caller passed a `Deferred:` finding, a `behavior: skip`, or a `Verification:` line with `differs:`
- something needs a person's judgment (a product call, how a screen looks): the `[!NOTE]` box becomes numbered `[!IMPORTANT]` items
- the change shows on a screen (screenshots), or compat-check returned ⚠️

**Before the draft leaves, call `Skill(skill: "gbase:unslop")` and rewrite the title and body by it, every table cell and bullet included.** Knowing its rules is not running it; the same holds for every later `gh pr edit --body`.

**5. Open.**

```bash
"${CLAUDE_SKILL_DIR}/scripts/ship-prep" open <draft>     # add --draft when the user or gbase:go passed it
```

It checks the draft (fix what it reports and rerun), pushes the branch, opens the PR, and prints `pr: <url>`. `--partial` when tracked files were left uncommitted on purpose; `--remote <name>` when the push doesn't go to `origin`. Put that line in the final report at column 0 ([format](../../references/orchestrator.md#report-lines)): `gbase:go` carries it up and a headless caller greps it. A failed push is never retried with force.

Leave the backup ref in place and say so in one line, with its `git update-ref -d` command (`gbase-run gc` removes it after 14 days).
