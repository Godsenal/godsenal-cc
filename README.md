# godsenal-cc

Development productivity plugins for Claude Code.

## Installation

Inside Claude Code, run these slash commands:

```
# 1. Add the marketplace
/plugin marketplace add Godsenal/godsenal-cc

# 2. Install the gbase plugin (includes all commands)
/plugin install gbase@godsenal

# (optional) Install the gapp plugin — app-building harness
/plugin install gapp@godsenal
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
- Then hands off to `/gbase:monitor` to babysit CI + reviews until the PR is merged or closed — including a post-PR **self-review** of the fresh PR, so review never slows the path to PR (`--no-review` to skip, `--draft` to open as a draft that flips to ready once CI is green and the review is resolved)
- Inherits all `branch-pr` safety rules — no force push, no hard reset; runs autonomously, stopping only for branch-pr's narrow "ask only when necessary" cases

**monitor** (skill) — Subscribe to the current branch's PR and keep it moving until merge/close.

- Packaged as a Skill (`plugins/base/skills/monitor/SKILL.md`)
- Model-invocable — triggers via `/gbase:monitor`, as the tail of `/gbase:go`, or when Claude judges you want a PR watched until merge (auto-triggering only starts the watch loop; ambiguous items still gate through `AskUserQuestion`)
- Resolves the PR via `gh`, sweeps current CI + reviews, then starts a persistent `Monitor` polling every 30s
- Runs one **self-review** of the PR (built-in `code-review`) right after the watch starts — it runs inside the CI wait the PR already pays, so it costs the ship path nothing; clear findings are auto-fixed in their own commits, the rest come back as a severity-ordered report; nothing is posted to GitHub (`--no-review` to skip; with `--draft`, flips the draft PR to ready once CI is green and the review is resolved)
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

**karpathy** (skill, model-invocable) — Merge Andrej Karpathy's four behavioral coding-agent guidelines into a project's `CLAUDE.md` in one command.

- Packaged as a Skill (`plugins/base/skills/karpathy/SKILL.md`)
- Inserts the four principles — **Think Before Coding**, **Simplicity First**, **Surgical Changes**, **Goal-Driven Execution** — as a marker-delimited managed block (text embedded verbatim, MIT, from the canonical `forrestchang/andrej-karpathy-skills`; not written by Karpathy himself)
- **Additive and idempotent**: never rewrites your project-specific content, and re-running updates the block in place instead of duplicating it; a no-op when already current
- Detects a hand-pasted copy of the rules and asks rather than duplicating; previews the exact block and confirms once before writing any governance file
- Targets the repo `CLAUDE.md` by default, `~/.claude/CLAUDE.md` with `--user`, or an explicit path; `--refresh` pulls the latest canonical text (pinned official repo only — never a fork URL), diffs it, then merges

### gapp

App-building harness — takes a raw app idea all the way to an App Store submission, one skill per stage. Every stage reads/writes `docs/HARNESS.md` (a living pipeline document), and every stage **auto-continues into the next one** unless the user says stop — you should never wonder "what do I run now". Distilled from shipping a real Expo + Supabase app (somandlee) end to end. Delegates to best-in-class skills when installed (gstack `office-hours` for idea validation, gstack `design-consultation` + taste skills for design) instead of reimplementing them.

Pipeline:

| Stage | Skill | What it does |
|---|---|---|
| 0 | **kickoff** | Office-hours-style idea interview (delegates to gstack `office-hours` if installed) — locks product/stack/design-direction/backend decisions, always fetching the *current* latest Expo SDK instead of trusting memory; creates `docs/HARNESS.md`, then flows straight into scaffold |
| 1 | **scaffold** | Expo project setup with battle-tested conventions: versioned-docs-only rule in the new repo's CLAUDE.md, bootstrap import order, `EXPO_PUBLIC_*` env discipline (never throw on missing config), pure-core + thin-IO test layout, DevMenu with state-reset + demo-seed actions, `theme/tokens.ts` skeleton |
| 2 | **design** | Design decision session using gstack `design-consultation`, taste skills, and `mobile-app-ui-design` (prompts installation if missing) — locks aesthetic/typography/color/spacing into real token values + `DESIGN.md`; enforces Korean-app font rules (no system-ui fallback) |
| 3 | **backend** | Supabase setup with the proven security model: RLS-gated reads, `security definer` RPCs for privileged writes (with mandatory permission pre-check — a recurring real-world bug), private storage + signed URLs only, `service_role` in Edge Functions only, append-only migrations, local-first/cloud-canonical sync with a `pending_ops` offline retry queue, plus a cloud integration smoke-test script |
| 4 | **cicd** | GitHub Actions + EAS: PR/main CI, main-push = OTA update, `v*` tag = native build + auto-submit, Supabase deploy on `supabase/**` — ships four generalized workflow templates (in `references/`) and walks the one-time setup checklist (secrets, channel↔branch link, submit credentials, branch protection) |
| 5 | **landing** | Marketing/landing site in the app monorepo's `web/` (static-first, Vercel Root=web, cleanUrls rewrite gotcha) — produces the privacy-policy and support URLs that store submission hard-requires |
| loop | **deploy** | The deploy runbook for the ongoing dev loop: auto-decides OTA vs native build from the diff (fingerprint runtime policy), runs preflight before native builds, executes with a single confirm gate before the irreversible trigger, and always reports what still needs a human (Apple review submission) |
| gate | **preflight** | Pre-release checklist gate: code (typecheck/test/expo-doctor/leftover temp code), backend (Supabase advisors/RLS pre-checks/smoke test/service_role leak grep), config (version bump, permission strings, secrets in history, channel link), store (privacy URL live, screenshot specs, metadata-vs-app consistency, demo account). PASS/FAIL table; fixes small FAILs itself |
| 6 | **store-assets** | Simulator-only App Store screenshots (preview-simulator build, demo-data seeding, screen forcing via Fast Refresh, dev-FAB removal via `simctl defaults`, `sips` resizing/padding) + complete store metadata doc (name/subtitle/keywords/privacy answers/age rating drafts) |
| 7 | **store-submit** | Claude-in-Chrome automation of App Store Connect: screenshot upload via ngrok tunnel + `DataTransfer` injection (native file dialogs and localhost fetch are both dead ends), React form filling via prototype setters, privacy/age-rating wizard loops (45s CDP timeout aware), and a human confirm gate before the final Submit-for-Review click; never touches Apple credentials |
| any | **next** | The resume button: reads `HARNESS.md`, reconciles it against actual repo state, then **runs** the next stage (not just a report) — the answer to "what do I do now?" |

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
/gbase:karpathy [--user]       # Merge Karpathy's behavioral guidelines into CLAUDE.md — additive + idempotent (skill)

/gapp:kickoff                  # New app idea → office-hours interview → decisions + HARNESS.md
/gapp:next                     # Resume: where am I? → runs the next stage automatically
/gapp:scaffold                 # Expo project setup (latest SDK, conventions, CLAUDE.md)
/gapp:design                   # Design decision session → tokens + DESIGN.md (taste skills)
/gapp:backend                  # Supabase backend with the proven security model
/gapp:cicd                     # GitHub Actions + EAS pipeline (OTA on main, build on v* tags)
/gapp:landing                  # Marketing site + privacy/support URLs (store prerequisites)
/gapp:deploy                   # Deploy runbook — auto-decides OTA vs native build
/gapp:preflight                # Pre-release checklist gate (code/backend/config/store)
/gapp:store-assets             # Simulator screenshots + store metadata
/gapp:store-submit             # App Store Connect submission via Claude-in-Chrome
```

## License

MIT
