# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

A Claude Code plugin marketplace (`godsenal`) containing the `gbase` and `gapp` plugins. No build step, no dependencies — plugins are pure markdown skill definitions.

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
      polish/
        SKILL.md                   ← polish skill: two-pass diff polish (deslop → structural), model-invocable; replaces /simplify and the bundled /code-review for the polish role
      go/
        SKILL.md                   ← go skill: polish → branch-pr → monitor one-shot
      monitor/
        SKILL.md                   ← monitor skill: subscribe to PR, handle CI / reviews / safe conflicts until merge; post-PR self-review via gbase:review (adversarial); runs polish before each non-trivial auto-fix commit
      review/
        SKILL.md                   ← review skill: adversarial code review — find (built-in code-review dimensions) → skeptic-verify each finding → drop refuted; local-only (no GitHub); replaces the built-in code-review for the self-review role in go/monitor
      pr-verify/
        SKILL.md                   ← pr-verify skill: open a PR's preview links in Claude-in-Chrome and verify behavior + design against PR body / diff / Figma / linked specs; reports to user, read-only on GitHub
      compat-check/
        SKILL.md                   ← compat-check skill: read-only diff analysis for backward-compat hazards (migrations, API/contract, queue schema, env/secrets, flags, backfills) → ordered rollout runbook; auto-invoked by branch-pr/go to inject a Rollout section into the PR body
      karpathy/
        SKILL.md                   ← karpathy skill: merge Karpathy's 4 behavioral guidelines (Think Before Coding / Simplicity First / Surgical Changes / Goal-Driven Execution) into a project's CLAUDE.md as a marker-delimited managed block — additive, idempotent, preview+confirm gate; text embedded verbatim (MIT, forrestchang/andrej-karpathy-skills)
      ego-profile/
        SKILL.md                   ← ego-profile skill: switch ego-browser to a different account/profile via listProfiles() + newTaskSpace(name, profileId) (positional, not an options object); covers the import-doesn't-switch-the-space trap, verifying the logged-in account via API before acting, and handing off for re-auth walls. Both helpers are absent from ego-browser's own SKILL.md
  app/                             ← gapp plugin: app-building harness (idea → App Store submission)
    .claude-plugin/plugin.json
    skills/                        ← every stage updates docs/HARNESS.md and auto-continues to the next stage ("이어달리기 규칙" in kickoff/SKILL.md)
      kickoff/SKILL.md             ← office-hours idea interview (delegates to gstack office-hours if installed) → decisions + docs/HARNESS.md
      scaffold/SKILL.md            ← Expo setup: latest-SDK lookup (never from memory), conventions, new repo's CLAUDE.md
      design/SKILL.md              ← design decision session via gstack design-consultation + taste/mobile-ui skills (installs if missing) → tokens + DESIGN.md
      backend/SKILL.md             ← Supabase: RLS + security-definer RPC model, append-only migrations, local-first sync, smoke test
      cicd/SKILL.md                ← GitHub Actions + EAS pipeline; references/ has 4 generalized workflow templates
        references/{ci,eas-update,eas-build,supabase-deploy}.yml
      analytics/SKILL.md           ← PostHog product analytics + error tracking + structured logs for web (Next.js) and app (Expo); lazy env reads, /ingest reverse proxy, OTel log pipeline for Node, worker flush discipline, app↔web person unification, MCP-verified delivery
      landing/SKILL.md             ← marketing site in web/ + privacy/support URLs (store submission prerequisites)
      deploy/SKILL.md              ← OTA-vs-native-build decision runbook, preflight before native builds, single confirm gate
      preflight/SKILL.md           ← pre-release checklist gate (code/backend/config/store), PASS/FAIL table, fixes small items
      store-assets/SKILL.md        ← simulator screenshot pipeline + store metadata doc
      store-submit/SKILL.md        ← Claude-in-Chrome ASC submission (ngrok+DataTransfer upload, React form setters, wizard loops); runs preflight first
      next/SKILL.md                ← resume button: read HARNESS.md, reconcile with repo state, RUN the next stage (not just report)
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

- **gbase**: Core productivity tools. Two commands and seven skills:
  - **find-skills** (command): Analyzes project tech stack (package.json, CLAUDE.md) and recommends matching skills from local repos and online marketplace. Supports `--online` flag for npx skills search.
  - **branch-pr** (command): Analyzes git changes, creates branch, groups files into logical commits, pushes, and creates PR via `gh`. **Runs fully autonomously** — decides the branch name, commit grouping, and PR body itself and ships without step-by-step confirmation; invoking it is the consent to push + open the PR. Stops only for a narrow "ask only when necessary" set (secret in the diff, unrelated WIP mixed in, ambiguous PR split, diverged branch, remote ambiguity). Before opening the PR it invokes `gbase:compat-check` and injects a `## Rollout / Deploy order` section when a sequenced rollout is needed; `--draft` opens the PR as a draft for `gbase:monitor` to flip to ready later. Keeps strict safety rules (no `git reset --hard`, no plain `--force`), stops when there's nothing to ship (guards against applying a stale stash), and keeps a persistent backup stash (`stash apply`, not `pop` — verified as freshly created before applying).
  - **compat-check** (skill, model-invocable): Read-only backward-compatibility / deploy-ordering analyzer at `plugins/base/skills/compat-check/SKILL.md`. Resolves a scope (args / current PR / uncommitted diff), scans for hazards that force a sequenced rollout — DB migrations (column drops/renames, `NOT NULL` without default, type narrowing, lock-heavy indexes), API/contract changes, message/queue schema changes, new required env/secrets, feature flags, data backfills, cache/serialization format changes, cross-service removals — and emits a one-line verdict (`✅ no special ordering` / `⚠️ requires ordered rollout`) plus, when needed, a numbered runbook (expand → migrate → backfill → deploy → flag ramp → follow-up contract PR) with rollback notes and `file:line` evidence. **Read-only**: never edits code, runs migrations/backfills, or deploys — it only describes the order, marking unverifiable commands `# verify`. Auto-invoked by `gbase:branch-pr` and (transitively) `gbase:go` during PR creation to inject a `## Rollout / Deploy order` section into the PR body when the verdict is `⚠️`; standalone via `/gbase:compat-check [range|paths]`.
  - **review** (skill, model-invocable): Adversarial code review at `plugins/base/skills/review/SKILL.md`. Built because the bundled `code-review` skill is no longer model-invocable, so `gbase:monitor` / `gbase:go` can't call it — this is the drop-in replacement for that self-review role. **Stage 1 (find)** replicates the built-in `code-review`'s dimensions — correctness & edge cases, bugs/regressions/missing error handling, security & data handling, clarity & consistency, test/doc gaps — at the same fewer-higher-signal bar; on non-trivial diffs it fans out to parallel per-dimension `Agent` sub-agents and dedupes by `file:line`. Every Stage 1 result is a **candidate, not a verdict**. **Stage 2 (adversarial verify)** hands each candidate to independent skeptic sub-agents *prompted to refute it* with a concrete counter-scenario (guarded upstream / invariant holds / caller never passes that input / dead branch), defaulting to refuted when uncertain; low/medium findings face one skeptic, high/critical ones a 3-skeptic majority panel — refuted candidates are dropped silently. **Stage 3 (classify & act)** runs survivors through the same clear-vs-ambiguous split as `monitor`: clear+local ones auto-fixed in their own commits (polished first via `gbase:polish`), everything else returned as a severity table + `review: F found, R refuted, S survived — A auto-fixed, K for you` tally with `AskUserQuestion` on judgment calls. **Local-only** — read-only on GitHub (no comments/reviews/replies/merges); reverts bad auto-fixes by reversing its own `Edit`, never `git checkout --`. Not polish (that's behavior-preserving cleanup) and not a GitHub actor. Explicit `/gbase:review` or invoked by `gbase:monitor` as the post-PR self-review.
  - **polish** (skill, model-invocable): Two-pass behavior-preserving diff polish at `plugins/base/skills/polish/SKILL.md`. Pass 1 is **deslop with 3-lens fan-out** — always spawns three parallel sub-agents (Lens A: AI cruft & dead code; Lens B: code reuse, unused imports, redundant vars, duplication; Lens C: clarity & efficiency — deep nesting, complex conditionals, hot-path perf wins), then a resolution step dedupes/filters/applies. Mirrors the original built-in `/simplify` design. Pass 2 is **structural** — ambitious "code judo" pass that collapses single-caller helpers, removes premature abstractions, flattens conditional growth, and fixes wrong-altitude band-aids (special cases layered on shared infrastructure); small contained edits apply directly, anything large (file moves, public API renames, >~50 lines) surfaces via `AskUserQuestion` first. After each pass, runs the lightest available correctness check (`tsc --noEmit`, focused tests) and reverts edits that break it — by reversing its own edits with `Edit`, never `git checkout --`/`git restore` (which would wipe the user's uncommitted work). Replaces `/simplify` and the bundled `/code-review` for the polish role inside `gbase:go` and `gbase:monitor`. Skips on pure renames, dependency bumps, generated code, prototype diffs.
  - **go** (skill, model-invocable): One-shot "finish a change" workflow at `plugins/base/skills/go/SKILL.md`. Invokes `/gbase:polish` on the current diff (or latest commit when the tree is clean), then `/gbase:branch-pr`, then `/gbase:monitor` back-to-back. Monitor's tail includes a post-PR adversarial self-review (`gbase:review`), so review adds nothing to the time-to-PR; `--draft` / `--no-review` pass through to the sub-skills. Triggers on explicit `/gbase:go` or when Claude judges the user has signalled a change is done and wants it shipped; each sub-step keeps its own consent and safety rules so the side effects stay gated.
  - **monitor** (skill, model-invocable): PR babysitter at `plugins/base/skills/monitor/SKILL.md`. Triggers on explicit `/gbase:monitor`, as the tail of `/gbase:go`, or when Claude judges the user wants a PR watched until merge — auto-triggering only starts the watch loop; the persistent `Monitor` + `AskUserQuestion` gates still block any unilateral edit/merge/force-push. Resolves the current branch's PR, sweeps CI + reviews + mergeability, then starts a persistent `Monitor` (30s poll) until merge/close. Right after the watch starts it runs one **adversarial self-review** of the PR via the `gbase:review` skill (our own, since the built-in `code-review` is no longer model-invocable) — each finding is verified against independent skeptics before surfacing, then goes through the same clear/ambiguous classification as reviewer comments (clear+local ones auto-fixed in their own commits, the rest reported to the user in a severity-ordered table); nothing from the self-review is posted to GitHub. `--no-review` skips it; with `--draft` it flips the draft PR to ready (`gh pr ready`) once CI is green and the self-review is resolved — the only case it may touch draft state. Auto-fixes clear CI failures, applies clearly-required review comments, and resolves safe merge conflicts (lockfile regen, pure-addition merges, whitespace-only) via rebase + `--force-with-lease`; runs `/gbase:polish` on every non-trivial auto-edit before committing. Always posts a reply back on the review item (applied / declined / deferred — with a one-line reason for declined items). Also surfaces testable preview/deploy links posted by CI/bots to the user (inline, with source + commit SHA, deduped; surface-only — never opens the link or comments back). Ambiguous items — semantic conflicts, design questions, migrations/schemas, config files — go through `AskUserQuestion`. Inherits `branch-pr` safety rules (no `git reset --hard`, no plain `--force`; `--force-with-lease` allowed only on conflict-resolution rebases).
  - **karpathy** (skill, model-invocable): One-command merge of Andrej Karpathy's four behavioral coding-agent guidelines into a project's `CLAUDE.md` at `plugins/base/skills/karpathy/SKILL.md`. Inserts **Think Before Coding / Simplicity First / Surgical Changes / Goal-Driven Execution** as a marker-delimited managed block (`<!-- BEGIN gbase:karpathy -->` … `<!-- END -->`). The rule text is **embedded verbatim** in the skill (MIT, distilled by Forrest Chang from Karpathy's Jan 2026 observations — *not* authored by Karpathy; the `multica-ai` fork the user may reference is a byte-identical copy) so it works offline and never pastes remote content unreviewed. **Additive + idempotent**: never rewrites project-specific content, replaces the block in place on re-run (no-op when already current), and detects a hand-pasted copy of the principles to avoid duplicating. Resolves the target as repo `CLAUDE.md` (default), `~/.claude/CLAUDE.md` (`--user`/`--global`), or an explicit path; `--refresh` fetches the **pinned canonical repo only** (never a fork URL passed at call time — malicious `CLAUDE.md` forks are a known exfiltration vector), diffs it, and asks before inserting an upstream-changed version. One write gate: previews the exact block/diff and confirms before touching the governance file. Explicit `/gbase:karpathy` or model-triggered on "add the karpathy rules / karpathy 룰 넣어줘".
  - **pr-verify** (skill, model-invocable): Browser-driven PR verification at `plugins/base/skills/pr-verify/SKILL.md`. The counterpart to `monitor`, which surfaces preview links but never opens them. Resolves a PR (URL / `owner/repo#123` / bare number / current branch), builds a `[behavior]`/`[design]`-tagged requirement checklist from four sources (PR body & checklists, the diff, linked Figma via the Figma MCP, linked issue/Notion/Jira specs), finds the newest preview/deploy link built from the head SHA, then opens it in Claude-in-Chrome — exercising each behavior item (clicks/typing + console-error check) and screenshot-comparing each design item against Figma (layout, spacing, color tokens, copy, states). Reports a per-requirement `PASS`/`FAIL`/`BLOCKED` table with screenshots to the user. **Read-only on GitHub** (never comments/approves/merges); **never enters credentials** (pauses for manual login on auth walls); never clicks destructive controls on the preview. Ambiguous cases — which preview, vague requirements, writes/irreversible actions, login, whole-file Figma links — go through `AskUserQuestion`.
