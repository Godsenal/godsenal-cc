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

> **출력 언어:** 모든 gbase 스킬은 사용자에게 보이는 텍스트(진행 보고, 리포트 표, `AskUserQuestion` 질문·옵션)를 **한국어**로 낸다. 코드·경로·명령어·고정 라벨(`critical`, `PASS`/`FAIL`, `✅`/`⚠️`)은 영어 그대로, 커밋 메시지·브랜치 이름·PR 본문은 대상 레포의 기존 관례를 따른다. 다른 언어로 요청하면 그 언어를 쓴다.

**find-skills** — Discover and install Claude Code skills matching your project's tech stack.

- Auto-analyzes `package.json` and `CLAUDE.md` to detect your stack
- Searches local skill repositories and online marketplace
- Recommends skills ranked by relevance
- Handles installation with proper agent scoping

**branch-pr** — Automate branch creation, intelligent commit grouping, and PR generation from current changes. **Runs fully autonomously** — invoking it is the go-ahead to branch, commit, push, and open the PR without step-by-step confirmation.

- Analyzes current git changes
- Decides the branch name and commit grouping itself (by layer, feature, or change type) — no "confirm?" prompts
- Pushes and opens a PR whose body is a reviewer briefing — **Why** (one sentence), **Change outline** (a diff sketch of the shape that changed, not a changelog), **Evidence** (before → after, plus the checks already run), **Merge danger** (risk tier from the touched paths · one-way/two-way door · blast radius, and how to revert), rollout order when compat-check flags one, and optional **Notes**. Combines humanlayer `visual-pr`, Matt Pocock's `pr`, and gbase's own risk/rollout. Fills the repo's own PR template instead when one exists
- Calls **compat-check** before opening the PR; injects a `## Rollout / Deploy order` section when a sequenced rollout is needed
- Stops only for the narrow "ask only when necessary" cases: a secret in the diff, unrelated WIP mixed in, an ambiguous PR split, a diverged branch, or remote ambiguity
- Keeps the destructive-command guardrails (no `git reset --hard`, no plain `--force`) and a persistent backup stash

**compat-check** (skill, model-invocable) — Scan a change for backward-compatibility hazards and get the safe deploy/script order.

- Packaged as a Skill (`plugins/base/skills/compat-check/SKILL.md`); read-only — never edits code, runs scripts, or deploys
- Reads a diff (uncommitted, a commit range, or a PR) and flags **migrations** (column drops, `NOT NULL` without default, type narrowing), **API/contract** changes, **queue/event schema** changes, new required **env/secrets**, **feature flags**, **backfill scripts**, **cache/serialization** format changes, **mobile client version skew** (old app versions still in the wild), and **native changes** that can't ship over OTA
- Emits a one-line verdict (`✅ No special deploy ordering needed` or `⚠️ Requires ordered rollout`) and, when needed, a numbered runbook (expand → migrate → backfill → deploy → ramp → follow-up contract PR) with a rollback note, each hazard mapped to `file:line`
- Auto-invoked by **branch-pr** / **go** to drop a `## Rollout / Deploy order` section into the PR body; also runs standalone via `/gbase:compat-check`

**blast-radius** (skill, model-invocable) — What could this change break *outside* the diff? Ported from pstack's `blast-radius`.

- Looks where grep stops: the called library's source at its pinned version (and local patches), execution timing, JSON/DB/wire formats, feature flags, code three hops downstream
- Finds the one fact the change is safe because of and **proves it by running code** — every claim is graded on a 5-step evidence ladder (said so → `file:line` → walked the failure → ran a script → reproduced in the app), and an unproven one is labelled `unproven`
- Deploy-ordering hazards are handed to `compat-check`; read-only on the repo (scratch scripts go to a temp dir)

**review** (skill, model-invocable) — Adversarial code review of the current change. The judgment layer on top of the built-in `code-review`: verification, and a gate deciding what may be fixed without asking.

- Packaged as a Skill (`plugins/base/skills/review/SKILL.md`); read-only on GitHub — never comments, reviews, replies, or merges
- **Stage 1 — Find** is *delegated* to the built-in `code-review` skill (`Skill(code-review, "medium")`), which runs in the background and returns findings labelled `CONFIRMED` / `PLAUSIBLE`. No hand-rolled finder — we inherit its dimensions and effort dial. `medium` is the default on purpose: above it the built-in routes to a multi-agent workflow fanning out to dozens of agents, and Stage 2 already recovers most of what the extra effort buys. Never `--fix` (it would bypass the gate below), never `--comment` (this skill is local-only), never `ultra` (user-triggered and billed). Falls back to an inline pass along the same dimensions if the built-in isn't available.
- **Stage 2 — Adversarial verify**: `PLAUSIBLE` findings go to independent skeptics prompted to *refute* them with a concrete counter-scenario; low/medium face one skeptic (batched 2–3 per skeptic when there are many, each still judged separately), high/critical a 3-skeptic majority panel. A `CONFIRMED` finding skips the panel only if it will merely be *reported* — if it would be auto-fixed, or is high/critical, it still faces a skeptic, because the built-in's verify is a single non-adversarial pass and auto-fixing is the irreversible half. Anything refuted is dropped. Low/medium skeptics run on Sonnet; the high/critical panel stays on the session's model, since a wrong refutation silently drops a real bug. Cleanup-category findings (reuse/simplification/efficiency) are filtered out before this stage — that's `polish`'s job, and they carry no failure scenario.
- **Repo rules**: a `REVIEW.md` (from `gbase:setup` or hand-written) governs every stage — skip paths, severity overrides, nit cap — and `CLAUDE.md` conventions are checked too
- **Stage 3 — Classify & act**: a defect on a line the diff didn't add is labelled `pre-existing` and reported, never auto-fixed (it would widen the PR and pin an old bug on this change); a pattern finding is fixed across every instance in the diff at once; clear+local survivors are auto-fixed; everything else comes back as a severity-ordered table + `review: F found, R refuted, S survived` tally. **Pre-PR mode** (from `go`) applies fixes as working-tree edits so `branch-pr` folds them into the initial commits, and *defers* judgment calls instead of asking; **post-PR mode** (from `monitor`) commits each fix separately.
- Invoke via `/gbase:review`, from `go` before the PR opens, or let `monitor` run it on a PR it didn't ship

**polish** (skill) — Two-pass behavior-preserving polish on the current diff. The polish role in `go` / `monitor`; distinct from the built-in `simplify` in its 3-lens fan-out, risk-split posture, recall gate, out-of-diff guard, and non-destructive revert.

- Packaged as a Skill (`plugins/base/skills/polish/SKILL.md`); model-invocable
- **Pass 1 — Deslop (3-lens fan-out)**: always spawns three parallel sub-agents — Lens A (AI cruft & dead code), Lens B (code reuse & duplication, unused imports, redundant vars), Lens C (clarity & efficiency, deep nesting, complex conditionals, hot-path perf wins). A resolution step then dedupes overlapping proposals, filters false positives, and applies the survivors.
- **Models**: the three lenses run on Sonnet (they only propose; the main agent resolves), Pass 2 on the session's model
- **Pass 2 — Structural**: ambitious "code judo" pass — collapses single-caller helpers, removes premature abstractions, suggests file splits, flattens conditional growth. Small contained edits apply directly; anything large (file moves, public API renames, >~50 lines) surfaces via `AskUserQuestion` first.
- **Verification**: after each pass, runs the lightest available correctness check (`tsc --noEmit`, focused tests) on touched files; reverts edits that break the check.
- Both passes preserve behavior; surfaces real bugs to the user instead of silently patching them
- Skips on pure renames, dependency bumps, generated code, prototype/throwaway diffs

**go** (skill) — Wrap up a working session in one shot: `review ∥ polish` → `verify` → `branch-pr` → `monitor`.

- Packaged as a Skill (`plugins/base/skills/go/SKILL.md`), not a legacy command
- Model-invocable — you can invoke `/gbase:go` explicitly, or Claude may auto-trigger it when you signal a change is done and want it shipped (sub-steps keep their own consent/safety gates)
- **Risk-scaled review**: classifies the change `low`/`medium`/`high` from the paths it touches (`REVIEW.md`'s always-high paths, or auth/payments/migrations/CI/app config); high-risk changes get `code-review high`, everything else `medium`
- **Launches the built-in `code-review` in the background, then runs `/gbase:polish` while it works.** Because the built-in forks to a background agent, review costs the ship path no wall-clock — and running it *before* the PR means fixes land in the initial commits instead of as churn on an open PR with a CI rerun per fix
- Hands the findings to `/gbase:review` for skeptic verification and the clear-vs-ambiguous gate; clear fixes are applied to the working tree, judgment calls are **deferred** and raised after the PR is open
- **Verification gate** — runs the project's *own* lint/typecheck/tests over the changed scope (from the `gbase:setup` verify block in `CLAUDE.md` when present), plus the repo's `verify-*` behavior skill for touched features when one exists; results land in the PR's `## Evidence` before anything is pushed (polish's check only validates polish's own edits, so a pre-existing failure would otherwise sail into CI). Biased toward shipping: pre-existing, flaky, and environment-dependent failures are noted and passed; only a diff-caused failure that resists two mechanical fix attempts stops the flow. `--no-verify` skips it
- Then `/gbase:branch-pr` (backup → branch → grouped commits → push → PR), then `/gbase:monitor --no-review` to babysit CI + reviews until merge
- **The PR still opens without asking.** Exactly two things can stop the flow before the PR exists: a diff-caused verification failure that isn't mechanically fixable, and branch-pr's narrow "ask only when necessary" cases. Everything else is carried and raised afterward
- Inherits all `branch-pr` safety rules — no force push, no hard reset

**monitor** (skill) — Subscribe to the current branch's PR and keep it moving until merge/close.

- Packaged as a Skill (`plugins/base/skills/monitor/SKILL.md`)
- Model-invocable — triggers via `/gbase:monitor`, as the tail of `/gbase:go`, or when Claude judges you want a PR watched until merge (auto-triggering only starts the watch loop; ambiguous items still gate through `AskUserQuestion`)
- Resolves the PR via `gh`, sweeps current CI + reviews, then starts a persistent `Monitor` polling every 30s
- Runs one **adversarial self-review** of the PR (`gbase:review`) right after the watch starts — inside the CI wait the PR already pays, so it costs the ship path nothing; findings are skeptic-verified, clear survivors are auto-fixed in their own commits, the rest come back as a severity-ordered report; nothing is posted to GitHub. This is for PRs `go` didn't ship (opened by an earlier session, a teammate, or by hand) — `go` reviews *before* the PR opens and passes `--no-review`. With `--draft`, flips the draft PR to ready once CI is green
- Auto-fixes clear CI failures (lint, format, type, unused imports) and applies clearly-required review comments (suggested diff blocks, typos, dead code)
- Resolves safe merge conflicts (lockfile regeneration, pure-addition merges, whitespace-only) via rebase + `--force-with-lease`; aborts and surfaces anything semantic
- Runs `/gbase:polish` on touched files before each auto-fix commit (skipped for pure lint/format output, verbatim `suggestion` block application, lockfile regen, and whitespace-only conflict resolution where polish would be a no-op)
- Surfaces testable preview/deploy links (app builds and OTA previews — EAS/TestFlight/Firebase App Distribution — or web previews like Vercel/Storybook/staging) that CI or bots post — inline, with source + commit SHA, deduped — so you know exactly what to click and test (surface-only; it never opens the link or comments back)
- Replies on every inline review comment it touches — `Addressed in <sha>.` for applied items, a one-line reason for declined ones, a "deferred to maintainer" note when waiting on a decision — so reviewers never wonder whether their comment was seen
- **Converges instead of looping** with automated reviewers: pre-existing findings get a one-line reply and no fix, repeats of handled findings are ignored, and after three rounds from the same reviewer it stops auto-applying and asks whether the approach needs rethinking
- Surfaces anything ambiguous (architecture, behavior, design questions, hedged feedback, semantic conflicts) via `AskUserQuestion`
- Stops automatically when the PR reaches `MERGED` or `CLOSED`

**setup** (skill, model-invocable) — Prepare a repo for the ship loop in one pass; idempotent, one confirmation.

- Records the project's verify commands (lint/typecheck/test/format, scoped variants, CI-only, known-failing) in a marker block in `CLAUDE.md` — **each command is run once before it's recorded**, so `go` never trusts a command that doesn't work
- Seeds a short `REVIEW.md` from repo evidence: what a defect means here, always-high-severity paths, skip paths, nit cap, `file:line` evidence required
- Adds a PostToolUse formatter hook to `.claude/settings.json` when the repo has a formatter (merged, never clobbered)
- Offers `create-verify` and `karpathy` when they're missing

**create-verify** (skill, model-invocable) — Generate a project-local `verify-<app>` skill that drives the real app the way a user does (web, Expo/iOS simulator, CLI, API) and captures evidence. Adapted from pstack's `create-verification-skill`.

- Interviews the repo, not the user: surface, run command, existing harness (Playwright/Maestro/Detox first), evidence, isolation
- Generated skill has Launch / Doctor / Drive / Evidence / Cleanup sections plus a per-feature map (`features/`, four fixed sections per feature)
- **Runs the generated skill end to end once** before handing it over — an unexecuted skill is reported as a draft
- `--maintain` audits the map against source (one read-only sub-agent per feature) and a live pass; fixes doc/harness drift, reports real regressions instead of papering over them
- `go` runs it for features the diff touches

**correct** (skill, model-invocable) — Turn mistakes agents keep repeating into checks. Adapted from pstack's `/correct` and Matt Pocock's `retro`.

- Mines recent commits, reverts, PR review comments, and past session transcripts (which hold pre-PR `review` reports that never reach GitHub); a class counts once it has happened twice
- Fixes each class at the highest level that works — architecture → types → lint/CI check whose error names the fix → test → `REVIEW.md` text last — after one multi-select confirmation
- Proves each new check fails on a real past instance, then passes on current code
- Judgment-call rules go to `REVIEW.md` (read by the reviewer, who has a diff and room), not `CLAUDE.md` (loaded into every session — pointers only); an existing-but-unwired check gets wired, not rebuilt
- Keeps an `## Enforced rules` table in `REVIEW.md` pairing each rule with what enforces it
- `--session` runs it as a retrospective on one session: slow navigation → a pointer, missing information → access (tee logs, read-only service access), expensive tool calls → a narrower command, checkable mistakes → the same ladder. Every candidate must cite a specific moment

**karpathy** (skill, model-invocable) — Merge Andrej Karpathy's four behavioral coding-agent guidelines into a project's `CLAUDE.md` in one command.

- Packaged as a Skill (`plugins/base/skills/karpathy/SKILL.md`)
- Inserts the four principles — **Think Before Coding**, **Simplicity First**, **Surgical Changes**, **Goal-Driven Execution** — as a marker-delimited managed block (text embedded verbatim, MIT, from the canonical `forrestchang/andrej-karpathy-skills`; not written by Karpathy himself)
- **Additive and idempotent**: never rewrites your project-specific content, and re-running updates the block in place instead of duplicating it; a no-op when already current
- Detects a hand-pasted copy of the rules and asks rather than duplicating; previews the exact block and confirms once before writing any governance file
- Targets the repo `CLAUDE.md` by default, `~/.claude/CLAUDE.md` with `--user`, or an explicit path; `--refresh` pulls the latest canonical text (pinned official repo only — never a fork URL), diffs it, then merges

**ego-profile** (skill, model-invocable) — Drive ego-browser as a *different* account when work and personal profiles are split.

- `listProfiles()` + `newTaskSpace(name, profileId)` — **positional args**, not an options object; both helpers are missing from ego-browser's own SKILL.md
- Documents the trap that cost a session: `import --browser chrome --profile X` reports success, but task spaces still open on the **default** profile, so the account never changes
- Verify the logged-in account over the service's API (`/api/users/@me/`) *before* acting — the UI looks signed in either way, and the mismatch only surfaces as "that project isn't in the list"
- Re-auth walls on sensitive settings (API keys, billing) stay a human step: hand off, wait for confirmation, take over
- Recovering an undocumented signature: call it wrong on purpose and read the error

### gapp

App-building harness — takes a raw app idea all the way to an App Store submission, one skill per stage. Every stage reads/writes `docs/HARNESS.md` (a living pipeline document), and every stage **auto-continues into the next one** unless the user says stop — you should never wonder "what do I run now". Distilled from shipping a real Expo + Supabase app (somandlee) end to end. Delegates to best-in-class skills when installed (gstack `office-hours` for idea validation, gstack `design-consultation` + taste skills for design) instead of reimplementing them.

> **출력 언어:** 모든 gapp 스킬은 사용자와의 대화(진행 보고, 판정 표, `AskUserQuestion`)를 **한국어**로 낸다. 단 **앱 산출물**(앱 UI 문구, 랜딩 카피, 개인정보/지원 페이지, 스토어 메타데이터)은 대화 언어가 아니라 `kickoff`에서 정한 **앱 언어**(`docs/HARNESS.md`)를 따른다. 코드·명령어·워크플로 YAML·상태 라벨은 영어 그대로.

Pipeline:

| Stage | Skill | What it does |
|---|---|---|
| 0 | **kickoff** | Office-hours-style idea interview (delegates to gstack `office-hours` if installed) — locks product/stack/design-direction/backend decisions, always fetching the *current* latest Expo SDK instead of trusting memory; creates `docs/HARNESS.md`, then flows straight into scaffold |
| 1 | **scaffold** | Expo project setup with battle-tested conventions: versioned-docs-only rule in the new repo's CLAUDE.md, bootstrap import order, `EXPO_PUBLIC_*` env discipline (never throw on missing config), pure-core + thin-IO test layout, DevMenu with state-reset + demo-seed actions, `theme/tokens.ts` skeleton |
| 2 | **design** | Design decision session using gstack `design-consultation`, taste skills, and `mobile-app-ui-design` (prompts installation if missing) — locks aesthetic/typography/color/spacing into real token values + `DESIGN.md`; enforces Korean-app font rules (no system-ui fallback) |
| 3 | **backend** | Supabase setup with the proven security model: RLS-gated reads, `security definer` RPCs for privileged writes (with mandatory permission pre-check — a recurring real-world bug), private storage + signed URLs only, `service_role` in Edge Functions only, append-only migrations, local-first/cloud-canonical sync with a `pending_ops` offline retry queue, plus a cloud integration smoke-test script |
| 4 | **cicd** | GitHub Actions + EAS: PR/main CI, main-push = OTA update, `v*` tag = native build + auto-submit, Supabase deploy on `supabase/**` — ships four generalized workflow templates (in `references/`) and walks the one-time setup checklist (secrets, channel↔branch link, submit credentials, branch protection) |
| 5 | **analytics** | PostHog in one pass — product analytics + error tracking + structured logs, wired into both the Next.js web app and the Expo app: lazy env resolution (module-scope `process.env` reads run *before* dotenv in worker scripts and silently disable all instrumentation), `/ingest` reverse-proxy rewrites with the middleware matcher exclusion, `_isIdentified()`-gated reset (a naive `reset()` re-rolls every anonymous visitor's id), OTel log pipeline for Node (the SDK has no `logger`, and PostHog's own doc example uses a stale positional `BatchLogRecordProcessor` signature), flush-before-exit discipline for cron workers, app↔web person unification over the WebView bridge, guarded source-map upload, and **end-to-end verification by querying PostHog over MCP** — "it built" is not verification |
| 6 | **landing** | Marketing/landing site in the app monorepo's `web/` (static-first, Vercel Root=web, cleanUrls rewrite gotcha) — produces the privacy-policy and support URLs that store submission hard-requires |
| loop | **deploy** | The deploy runbook for the ongoing dev loop: auto-decides OTA vs native build from the diff (fingerprint runtime policy), runs preflight before native builds, executes with a single confirm gate before the irreversible trigger, and always reports what still needs a human (Apple review submission) |
| gate | **preflight** | Pre-release checklist gate: code (typecheck/test/expo-doctor/leftover temp code), backend (Supabase advisors/RLS pre-checks/smoke test/service_role leak grep), config (version bump, permission strings, secrets in history, channel link), store (privacy URL live, screenshot specs, metadata-vs-app consistency, demo account). PASS/FAIL table; fixes small FAILs itself |
| 7 | **store-assets** | Simulator-only App Store screenshots (preview-simulator build, demo-data seeding, screen forcing via Fast Refresh, dev-FAB removal via `simctl defaults`, `sips` resizing/padding) + complete store metadata doc (name/subtitle/keywords/privacy answers/age rating drafts) |
| 8 | **store-submit** | Claude-in-Chrome automation of App Store Connect: screenshot upload via ngrok tunnel + `DataTransfer` injection (native file dialogs and localhost fetch are both dead ends), React form filling via prototype setters, privacy/age-rating wizard loops (45s CDP timeout aware), and a human confirm gate before the final Submit-for-Review click; never touches Apple credentials |
| any | **next** | The resume button: reads `HARNESS.md`, reconciles it against actual repo state, then **runs** the next stage (not just a report) — the answer to "what do I do now?" |

## Usage

After installation, the following are available:

```
/gbase:find-skills             # Discover skills for your project (command)
/gbase:branch-pr               # Autonomous branch + commit + PR from current changes (command)
/gbase:compat-check [range]    # Flag backward-compat hazards + emit a deploy-order runbook (skill, model-invocable)
/gbase:polish                  # Two-pass diff polish — deslop + structural (skill, model-invocable)
/gbase:blast-radius            # What could this break beyond the diff — proven by running code (skill)
/gbase:review                  # Adversarial review — built-in code-review + skeptic verify (skill, model-invocable)
/gbase:go                      # Review ∥ polish → verify → branch + commit + PR → monitor (skill)
/gbase:monitor                 # Watch current branch's PR — auto-fix clear CI/review items (skill)
/gbase:setup                   # Record verify commands, seed REVIEW.md, add format hook (skill)
/gbase:create-verify [--maintain]  # Generate/maintain a project-local behavior-verification skill (skill)
/gbase:correct [--session]     # Turn recurring review/CI mistakes into checks; --session = retro on one session (skill)
/gbase:karpathy [--user]       # Merge Karpathy's behavioral guidelines into CLAUDE.md — additive + idempotent (skill)
/gbase:ego-profile             # Switch ego-browser to another account/profile (skill, model-invocable)

/gapp:kickoff                  # New app idea → office-hours interview → decisions + HARNESS.md
/gapp:next                     # Resume: where am I? → runs the next stage automatically
/gapp:scaffold                 # Expo project setup (latest SDK, conventions, CLAUDE.md)
/gapp:design                   # Design decision session → tokens + DESIGN.md (taste skills)
/gapp:backend                  # Supabase backend with the proven security model
/gapp:cicd                     # GitHub Actions + EAS pipeline (OTA on main, build on v* tags)
/gapp:analytics                # PostHog: product analytics + error tracking + logs (web + app)
/gapp:landing                  # Marketing site + privacy/support URLs (store prerequisites)
/gapp:deploy                   # Deploy runbook — auto-decides OTA vs native build
/gapp:preflight                # Pre-release checklist gate (code/backend/config/store)
/gapp:store-assets             # Simulator screenshots + store metadata
/gapp:store-submit             # App Store Connect submission via Claude-in-Chrome
```

## License

MIT
