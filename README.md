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

**go** (skill) — Wrap up a working session in one shot: run `simplify` on recent code, then run `branch-pr` end-to-end.

- Packaged as a Skill (`plugins/base/skills/go/SKILL.md`), not a legacy command
- `disable-model-invocation: true` — only triggers when you explicitly invoke `/gbase:go`; Claude won't auto-run it
- Invokes the official bundled `/simplify` skill on the current diff (or the latest commit if the tree is clean)
- Then invokes `/gbase:branch-pr` for the full flow (backup → branch → grouped commits → push → PR)
- Inherits all `branch-pr` safety rules — no force push, no hard reset, step-by-step confirmation

## Usage

After installation, the following are available:

```
/gbase:find-skills             # Discover skills for your project (command)
/gbase:branch-pr               # Branch + commit + PR from current changes (command)
/gbase:go                      # Simplify recent code → then branch + commit + PR (skill)
```

## License

MIT
