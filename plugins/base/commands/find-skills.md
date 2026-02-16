---
description: Find skills that match your project's tech stack
---

[FIND SKILLS MODE]

$ARGUMENTS

## Skill Finder

You are now in skill discovery mode. Your task is to find and recommend Claude Code skills that match the current project's tech stack.

### Arguments Parsing

First, parse the arguments:
- No arguments: Auto-analyze mode (analyze package.json and CLAUDE.md)
- Has `--online` flag: Include online search via `npx skills find`
- Other arguments: Use as search keywords

### Skill Search Locations

**Local Repositories (always search):**
1. `~/.claude/skills/anthropic-skills/skills/` - Official Anthropic skills
2. `~/.claude/skills/antigravity-awesome-skills/skills/` - Community collection
3. `~/.claude/skills/everything-claude-code/` - agents/, rules/, contexts/
4. `~/.claude/skills/ui-ux-pro-max-skill/` - UI/UX design system

**Online Sources (if --online flag):**
- Use `npx skills find [keyword]` to search skills.sh marketplace
- https://skills.sh - Skills marketplace
- https://github.com/anthropics/skills - Official repository

### Execution Steps

#### Step 1: Determine Mode

Check the arguments:
```
If arguments contain "--online":
  → Online search mode with any remaining keywords
Else if arguments are empty:
  → Auto-analyze mode
Else:
  → Keyword search mode
```

#### Step 2: Auto-Analyze Mode (if no arguments)

1. **Read package.json** (if exists):
   - Extract `dependencies` and `devDependencies`
   - Identify frameworks: next, react, vue, angular, express, fastify, etc.
   - Identify tools: typescript, tailwind, drizzle, prisma, jest, playwright, etc.

2. **Read CLAUDE.md** (if exists):
   - Extract tech stack information
   - Identify domain (e.g., game, e-commerce, dashboard)

3. **Generate Keywords** from analysis:
   - Framework names (nextjs, react, vue)
   - ORM/DB tools (drizzle, prisma, postgres, supabase)
   - Styling (tailwind, css, ui)
   - Testing (jest, playwright, testing)
   - AI/ML if relevant (ai, llm, openai, gemini)

#### Step 3: Search Local Skills

For each skill repository:

1. **Anthropic Skills** (`~/.claude/skills/anthropic-skills/skills/`):
   - List all SKILL.md files
   - Match directory names and descriptions against keywords

2. **Antigravity Skills** (`~/.claude/skills/antigravity-awesome-skills/skills/`):
   - Search directory names
   - Read README.md for skill descriptions

3. **Everything Claude Code** (`~/.claude/skills/everything-claude-code/`):
   - Search agents/, rules/, contexts/ directories
   - Match file names against keywords

4. **UI/UX Pro Max** (`~/.claude/skills/ui-ux-pro-max-skill/`):
   - Always relevant for frontend projects
   - Include if project has React, Vue, or UI keywords

#### Step 4: Online Search (if --online flag)

Use `npx skills find [keyword]` to search for skills:
```bash
npx skills find typescript
npx skills find monorepo
npx skills find [detected-framework]
```

#### Step 5: Present Results

Output format:

```markdown
# Skill Recommendations for [Project Name]

## Detected Tech Stack
- **Framework:** [e.g., Next.js 14]
- **Language:** [e.g., TypeScript]
- **Database:** [e.g., PostgreSQL with Drizzle]
- **Styling:** [e.g., Tailwind CSS, shadcn/ui]

## Recommended Skills

### High Relevance
| Skill | Source | Install Command |
|-------|--------|-----------------|
| mcp-builder | anthropics/skills | See below |

### Medium Relevance
| Skill | Source | Install Command |
|-------|--------|-----------------|
```

#### Step 6: Ask Installation Scope (IMPORTANT)

**ALWAYS ask the user before installing:**

Use AskUserQuestion to ask:
- **Question:** "Where should I install the skills?"
- **Options:**
  1. **Project local** (Recommended) - Install to `.claude/skills/` in this project only
  2. **Global** - Install to `~/.claude/skills/` for all projects

#### Step 7: Detect Current Agent

Before installing, detect which AI agent/IDE the user is using by checking for config directories:

```bash
# Check which agent configs exist in the project
ls -d .claude .cursor .cline .windsurf .codex 2>/dev/null
```

**Agent Detection Priority:**
1. If running in Claude Code → use `claude-code`
2. If `.cursor/` exists → user might use Cursor too
3. If `.cline/` exists → user might use Cline too
4. Default to `claude-code` for this skill

**Common agent names for -a flag:**
- `claude-code` - Claude Code CLI
- `cursor` - Cursor IDE
- `cline` - Cline extension
- `windsurf` - Windsurf
- `codex` - OpenAI Codex

#### Step 8: Install Skills

**For Project Local (Recommended):**
```bash
# Use -a flag to specify ONLY the agent you need
# This prevents creating 30+ unnecessary directories
npx skills add owner/repo@skill-name -a claude-code -y
```

**For Global:**
```bash
# Global install with specific agent
npx skills add owner/repo@skill-name -g -a claude-code -y
```

### Skills CLI Options Reference

```
npx skills add <source> [options]

Options:
  -g, --global           Install globally (user-level) instead of project-level
  -a, --agent <agents>   Specify agents to install to (IMPORTANT: use this!)
  -s, --skill <skills>   Specify skill names to install
  -y, --yes              Skip confirmation prompts
  --all                  Install all skills to all agents (avoid this)

Examples:
  npx skills add anthropics/skills@mcp-builder -a claude-code -y
  npx skills add wshobson/agents@typescript -a claude-code cursor -y
  npx skills add vercel-labs/agent-skills -g -a claude-code -y
```

### Why Use -a Flag?

Without `-a` flag, skills CLI installs to ALL 30+ supported agents:
- Creates `.cline/`, `.cursor/`, `.codex/`, `.windsurf/`, etc.
- Pollutes your project root with unnecessary directories
- Wastes time and disk space

With `-a claude-code`:
- Only creates `.claude/skills/`
- Clean and minimal
- Fast installation

### Keyword Mappings

Use these mappings to expand search:

| Technology | Keywords to Search |
|------------|-------------------|
| Next.js | nextjs, next, react, ssr, server-components |
| React | react, frontend, ui, hooks, components |
| Tailwind | tailwind, css, styling, ui |
| PostgreSQL | postgres, database, sql, db |
| Drizzle | drizzle, orm, database |
| Prisma | prisma, orm, database |
| TypeScript | typescript, ts, types |
| Testing | testing, test, jest, playwright, vitest |
| AI/LLM | ai, llm, openai, gemini, anthropic, claude |
| Supabase | supabase, postgres, auth, realtime |
| MCP | mcp, model-context-protocol, mcp-server |
| Monorepo | monorepo, turborepo, nx, workspaces |

---

Now analyze the project and find matching skills!
