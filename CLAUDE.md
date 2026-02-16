# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

A Claude Code plugin marketplace (`godsenal`) containing two plugins. No build step, no dependencies — plugins are pure markdown skill definitions.

## Architecture

```
.claude-plugin/marketplace.json    ← Marketplace registry (lists all plugins)
plugins/
  <name>/
    .claude-plugin/plugin.json     ← Plugin metadata (name, version, author, keywords)
    commands/<name>.md             ← Skill definition (frontmatter + prompt)
```

**Marketplace JSON** at root registers plugins with `source` paths pointing to each plugin directory. Each plugin's `commands/*.md` file is the actual skill — a markdown file with YAML frontmatter (`description`, `allowed-tools`) followed by the prompt template.

## Adding a New Plugin

1. Create `plugins/<name>/commands/<name>.md` with frontmatter and prompt
2. Create `plugins/<name>/.claude-plugin/plugin.json` with name, version, description, author, repository, license, keywords, category
3. Add an entry to `.claude-plugin/marketplace.json` under `plugins[]`
4. Update `README.md` with the plugin description and usage

## Testing

No automated tests. Validate manually:
- JSON validity: `python3 -c "import json; json.load(open('<file>'))"` for each plugin.json and marketplace.json
- Local install: `/plugin marketplace add ./` (inside Claude Code)
- Plugin install: `/plugin install find-skills@godsenal`
- Commands: `/godsenal:find-skills`, `/godsenal:branch-pr`

## Current Plugins

- **find-skills**: Analyzes project tech stack (package.json, CLAUDE.md) and recommends matching skills from local repos and online marketplace. Supports `--online` flag for npx skills search.
- **branch-pr**: Analyzes git changes, creates branch, groups files into logical commits, pushes, and creates PR via `gh`. Has strict safety rules (no force push, no hard reset). Requires user confirmation at each step.
