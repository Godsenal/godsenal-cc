# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

A Claude Code plugin marketplace (`godsenal`) containing the `gbase` plugin. No build step, no dependencies — plugins are pure markdown skill definitions.

**Naming convention:** Plugin names use a `g` prefix (e.g. `gbase`, `gfe`), while directory names omit it (e.g. `plugins/base/`, `plugins/fe/`).

## Architecture

```
.claude-plugin/marketplace.json    ← Marketplace registry (lists all plugins)
plugins/
  base/
    .claude-plugin/plugin.json     ← Plugin metadata (name, version, author, keywords)
    commands/                      ← Legacy commands (still supported, but new work should go in skills/)
      find-skills.md
      branch-pr.md
    skills/                        ← Skills (preferred — commands have been merged into skills per Claude Code docs)
      go/
        SKILL.md                   ← go skill: code-review → branch-pr → monitor one-shot
      monitor/
        SKILL.md                   ← monitor skill: subscribe to PR, handle CI / reviews / safe conflicts until merge
```

**Marketplace JSON** at root registers plugins with `source` paths pointing to each plugin directory. Commands and skills both surface as `/gbase:<name>` invocations. Skills (`skills/<name>/SKILL.md`) support extra frontmatter that commands don't — notably `disable-model-invocation: true` to prevent Claude from auto-triggering them.

## Adding a New Skill to base (preferred)

1. Create `plugins/base/skills/<name>/SKILL.md` with frontmatter (`name`, `description`, optional `disable-model-invocation`, `allowed-tools`) and body
2. Update `plugins/base/.claude-plugin/plugin.json` keywords if needed
3. Update `README.md` with the skill description and usage

## Adding a New Command to base (legacy)

Use only when migrating existing files or for parity with older tooling. New work should go under `skills/`.

1. Create `plugins/base/commands/<name>.md` with frontmatter and prompt
2. Update `plugins/base/.claude-plugin/plugin.json` keywords if needed
3. Update `README.md` with the command description and usage

## Adding a New Plugin

1. Create `plugins/<name>/commands/<name>.md` with frontmatter and prompt
2. Create `plugins/<name>/.claude-plugin/plugin.json` with name, version, description, author, repository, license, keywords, category
3. Add an entry to `.claude-plugin/marketplace.json` under `plugins[]`
4. Update `README.md` with the plugin description and usage

## Testing

No automated tests. Validate manually:
- JSON validity: `python3 -c "import json; json.load(open('<file>'))"` for each plugin.json and marketplace.json
- Local install: `/plugin marketplace add ./` (inside Claude Code)
- Plugin install: `/plugin install gbase@godsenal`
- Commands: `/gbase:find-skills`, `/gbase:branch-pr`

## Current Plugins

- **gbase**: Core productivity tools. Two commands and two skills:
  - **find-skills** (command): Analyzes project tech stack (package.json, CLAUDE.md) and recommends matching skills from local repos and online marketplace. Supports `--online` flag for npx skills search.
  - **branch-pr** (command): Analyzes git changes, creates branch, groups files into logical commits, pushes, and creates PR via `gh`. Has strict safety rules (no force push, no hard reset). Requires user confirmation at each step.
  - **go** (skill, `disable-model-invocation: true`): One-shot "finish a change" workflow at `plugins/base/skills/go/SKILL.md`. Invokes the bundled `/code-review` skill on the current diff (or latest commit when the tree is clean), then `/gbase:branch-pr`, then `/gbase:monitor` back-to-back. Only triggers on explicit `/gbase:go` — Claude will not auto-run it.
  - **monitor** (skill, `disable-model-invocation: true`): PR babysitter at `plugins/base/skills/monitor/SKILL.md`. Resolves the current branch's PR, sweeps CI + reviews + mergeability, then starts a persistent `Monitor` (30s poll) until merge/close. Auto-fixes clear CI failures, applies clearly-required review comments, and resolves safe merge conflicts (lockfile regen, pure-addition merges, whitespace-only) via rebase + `--force-with-lease`; runs the bundled `code-review` skill on every non-trivial auto-edit before committing. Always posts a reply back on the review item (applied / declined / deferred — with a one-line reason for declined items). Ambiguous items — semantic conflicts, design questions, migrations/schemas, config files — go through `AskUserQuestion`. Inherits `branch-pr` safety rules (no `git reset --hard`, no plain `--force`; `--force-with-lease` allowed only on conflict-resolution rebases).
