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

Core productivity tools for Claude Code — skill discovery and automated branch/PR workflows.

**find-skills** — Discover and install Claude Code skills matching your project's tech stack.

- Auto-analyzes `package.json` and `CLAUDE.md` to detect your stack
- Searches local skill repositories and online marketplace
- Recommends skills ranked by relevance
- Handles installation with proper agent scoping

**branch-pr** — Automate branch creation, intelligent commit grouping, and PR generation from current changes.

- Analyzes current git changes
- Creates a properly named branch
- Groups files into logical commits (by layer, feature, or change type)
- Generates a PR with summary, changes, and test plan
- Includes safety rails and backup/recovery at every step

**go** (skill) — Wrap up a working session in one shot: `code-review` → `branch-pr` → `monitor`.

- Packaged as a Skill (`plugins/base/skills/go/SKILL.md`), not a legacy command
- `disable-model-invocation: true` — only triggers when you explicitly invoke `/gbase:go`; Claude won't auto-run it
- Invokes the official bundled `/code-review` skill on the current diff (or the latest commit if the tree is clean)
- Then invokes `/gbase:branch-pr` for the full flow (backup → branch → grouped commits → push → PR)
- Then hands off to `/gbase:monitor` to babysit CI + reviews until the PR is merged or closed
- Inherits all `branch-pr` safety rules — no force push, no hard reset, step-by-step confirmation

**monitor** (skill) — Subscribe to the current branch's PR and keep it moving until merge/close.

- Packaged as a Skill (`plugins/base/skills/monitor/SKILL.md`)
- `disable-model-invocation: true` — only triggers via `/gbase:monitor` or as the tail of `/gbase:go`
- Resolves the PR via `gh`, sweeps current CI + reviews, then starts a persistent `Monitor` polling every 30s
- Auto-fixes clear CI failures (lint, format, type, unused imports) and applies clearly-required review comments (suggested diff blocks, typos, dead code)
- Resolves safe merge conflicts (lockfile regeneration, pure-addition merges, whitespace-only) via rebase + `--force-with-lease`; aborts and surfaces anything semantic
- Runs the bundled `/code-review` skill on touched files before each auto-fix commit (skipped for pure lint/format output, verbatim `suggestion` block application, lockfile regen, and whitespace-only conflict resolution where code-review would be a no-op)
- Replies on every inline review comment it touches — `Addressed in <sha>.` for applied items, a one-line reason for declined ones, a "deferred to maintainer" note when waiting on a decision — so reviewers never wonder whether their comment was seen
- Surfaces anything ambiguous (architecture, behavior, design questions, hedged feedback, semantic conflicts) via `AskUserQuestion`
- Stops automatically when the PR reaches `MERGED` or `CLOSED`

## Usage

After installation, the following are available:

```
/gbase:find-skills             # Discover skills for your project (command)
/gbase:branch-pr               # Branch + commit + PR from current changes (command)
/gbase:go                      # Code review → branch + commit + PR → monitor (skill)
/gbase:monitor                 # Watch current branch's PR — auto-fix clear CI/review items (skill)
```

## License

MIT
