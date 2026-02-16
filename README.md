# godsenal-cc

Development productivity plugins for Claude Code.

## Plugins

### find-skills

Discover and install Claude Code skills matching your project's tech stack.

- Auto-analyzes `package.json` and `CLAUDE.md` to detect your stack
- Searches local skill repositories and online marketplace
- Recommends skills ranked by relevance
- Handles installation with proper agent scoping

### branch-pr

Automate branch creation, intelligent commit grouping, and PR generation from current changes.

- Analyzes current git changes
- Creates a properly named branch
- Groups files into logical commits (by layer, feature, or change type)
- Generates a PR with summary, changes, and test plan
- Includes safety rails and backup/recovery at every step

## Installation

```bash
claude plugin add godsenal/godsenal-cc
```

## Usage

After installation, the following commands become available:

```
/godsenal:find-skills          # Discover skills for your project
/godsenal:branch-pr            # Branch + commit + PR from current changes
```

## License

MIT
