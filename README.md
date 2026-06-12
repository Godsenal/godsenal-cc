# godsenal-cc

Development productivity plugins for Claude Code.

## Installation

Inside Claude Code, run these slash commands:

```
# 1. Add the marketplace
/plugin marketplace add Godsenal/godsenal-cc

# 2. Install the gbase plugin (includes all commands)
/plugin install gbase@godsenal
```

Or browse interactively with `/plugin` and go to the **Discover** tab.

## Plugins

### gbase

Core productivity tools for Claude Code — skill discovery, autonomous branch/PR workflows, and backward-compat deploy-order checks.

**find-skills** — Discover and install Claude Code skills matching your project's tech stack.

- Auto-analyzes `package.json` and `CLAUDE.md` to detect your stack
- Searches local skill repositories and online marketplace
- Recommends skills ranked by relevance
- Handles installation with proper agent scoping

**branch-pr** — Automate branch creation, intelligent commit grouping, and PR generation from current changes. **Runs fully autonomously** — invoking it is the go-ahead to branch, commit, push, and open the PR without step-by-step confirmation.

- Analyzes current git changes
- Decides the branch name and commit grouping itself (by layer, feature, or change type) — no "confirm?" prompts
- Pushes and opens a PR with summary, changes, and test plan
- Calls **compat-check** before opening the PR; injects a `## Rollout / Deploy order` section when a sequenced rollout is needed
- Stops only for the narrow "ask only when necessary" cases: a secret in the diff, unrelated WIP mixed in, an ambiguous PR split, a diverged branch, or remote ambiguity
- Keeps the destructive-command guardrails (no `git reset --hard`, no plain `--force`) and a persistent backup stash

**compat-check** (skill, model-invocable) — Scan a change for backward-compatibility hazards and get the safe deploy/script order.

- Packaged as a Skill (`plugins/base/skills/compat-check/SKILL.md`); read-only — never edits code, runs scripts, or deploys
- Reads a diff (uncommitted, a commit range, or a PR) and flags **migrations** (column drops, `NOT NULL` without default, type narrowing), **API/contract** changes, **queue/event schema** changes, new required **env/secrets**, **feature flags**, **backfill scripts**, and **cache/serialization** format changes
- Emits a one-line verdict (`✅ no special ordering` or `⚠️ requires ordered rollout`) and, when needed, a numbered runbook (expand → migrate → backfill → deploy → ramp → follow-up contract PR) with a rollback note, each hazard mapped to `file:line`
- Auto-invoked by **branch-pr** / **go** to drop a `## Rollout / Deploy order` section into the PR body; also runs standalone via `/gbase:compat-check`

**polish** (skill) — Two-pass behavior-preserving polish on the current diff. Replaces `/simplify` and the bundled `/code-review` for the polish role.

- Packaged as a Skill (`plugins/base/skills/polish/SKILL.md`); model-invocable
- **Pass 1 — Deslop (3-lens fan-out)**: always spawns three parallel sub-agents — Lens A (AI cruft & dead code), Lens B (code reuse & duplication, unused imports, redundant vars), Lens C (clarity & efficiency, deep nesting, complex conditionals, hot-path perf wins). A resolution step then dedupes overlapping proposals, filters false positives, and applies the survivors. Mirrors the original built-in `/simplify` design.
- **Pass 2 — Structural**: ambitious "code judo" pass — collapses single-caller helpers, removes premature abstractions, suggests file splits, flattens conditional growth. Small contained edits apply directly; anything large (file moves, public API renames, >~50 lines) surfaces via `AskUserQuestion` first.
- **Verification**: after each pass, runs the lightest available correctness check (`tsc --noEmit`, focused tests) on touched files; reverts edits that break the check.
- Both passes preserve behavior; surfaces real bugs to the user instead of silently patching them
- Skips on pure renames, dependency bumps, generated code, prototype/throwaway diffs

**go** (skill) — Wrap up a working session in one shot: `polish` → `branch-pr` → `monitor`.

- Packaged as a Skill (`plugins/base/skills/go/SKILL.md`), not a legacy command
- Model-invocable — you can invoke `/gbase:go` explicitly, or Claude may auto-trigger it when you signal a change is done and want it shipped (sub-steps keep their own consent/safety gates)
- Invokes `/gbase:polish` (deslop + structural) on the current diff (or the latest commit if the tree is clean)
- Then invokes `/gbase:branch-pr` for the full flow (backup → branch → grouped commits → push → PR)
- Then hands off to `/gbase:monitor` to babysit CI + reviews until the PR is merged or closed
- Inherits all `branch-pr` safety rules — no force push, no hard reset, step-by-step confirmation

**monitor** (skill) — Subscribe to the current branch's PR and keep it moving until merge/close.

- Packaged as a Skill (`plugins/base/skills/monitor/SKILL.md`)
- Model-invocable — triggers via `/gbase:monitor`, as the tail of `/gbase:go`, or when Claude judges you want a PR watched until merge (auto-triggering only starts the watch loop; ambiguous items still gate through `AskUserQuestion`)
- Resolves the PR via `gh`, sweeps current CI + reviews, then starts a persistent `Monitor` polling every 30s
- Auto-fixes clear CI failures (lint, format, type, unused imports) and applies clearly-required review comments (suggested diff blocks, typos, dead code)
- Resolves safe merge conflicts (lockfile regeneration, pure-addition merges, whitespace-only) via rebase + `--force-with-lease`; aborts and surfaces anything semantic
- Runs `/gbase:polish` on touched files before each auto-fix commit (skipped for pure lint/format output, verbatim `suggestion` block application, lockfile regen, and whitespace-only conflict resolution where polish would be a no-op)
- Surfaces testable preview/deploy links (Vercel/Netlify/Storybook/staging, etc.) that CI or bots post — inline, with source + commit SHA, deduped — so you know exactly what to click and test (surface-only; it never opens the link or comments back)
- Replies on every inline review comment it touches — `Addressed in <sha>.` for applied items, a one-line reason for declined ones, a "deferred to maintainer" note when waiting on a decision — so reviewers never wonder whether their comment was seen
- Surfaces anything ambiguous (architecture, behavior, design questions, hedged feedback, semantic conflicts) via `AskUserQuestion`
- Stops automatically when the PR reaches `MERGED` or `CLOSED`

**pr-verify** (skill, model-invocable) — Throw it a PR and it verifies the change actually works in the browser. The counterpart to `monitor`, which surfaces preview links but never opens them.

- Packaged as a Skill (`plugins/base/skills/pr-verify/SKILL.md`); model-invocable
- Resolves a PR (URL / `owner/repo#123` / bare number / current branch) and builds a requirement checklist from **four sources**: the PR body & checklists, the diff, linked **Figma** designs (via the Figma MCP), and linked issue/Notion/Jira specs — each item tagged `[behavior]` or `[design]`
- Finds the PR's preview/deploy link (Vercel/Netlify/Storybook/staging, newest build from the head SHA) and opens it in **Claude-in-Chrome**
- Drives each `[behavior]` item (clicks/typing, console-error check) and screenshot-compares each `[design]` item against Figma (layout, spacing, color tokens, copy, states)
- Reports a per-requirement `PASS`/`FAIL`/`BLOCKED` table with screenshots **to you** — read-only on GitHub, never comments/approves/merges
- Never enters credentials — on a login wall it pauses and asks you to sign in manually; never clicks destructive controls on the preview
- Surfaces ambiguity (which preview, vague requirements, writes needed, login, whole-file Figma links) via `AskUserQuestion`

## Usage

After installation, the following are available:

```
/gbase:find-skills             # Discover skills for your project (command)
/gbase:branch-pr               # Autonomous branch + commit + PR from current changes (command)
/gbase:compat-check [range]    # Flag backward-compat hazards + emit a deploy-order runbook (skill, model-invocable)
/gbase:polish                  # Two-pass diff polish — deslop + structural (skill, model-invocable)
/gbase:go                      # Polish → branch + commit + PR → monitor (skill)
/gbase:monitor                 # Watch current branch's PR — auto-fix clear CI/review items (skill)
/gbase:pr-verify <pr>          # Verify a PR's behavior + design in the browser via Claude-in-Chrome (skill)
```

## License

MIT
