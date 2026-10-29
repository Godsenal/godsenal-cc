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

# (optional) Install the gshorts plugin — faceless Korean short-form videos, Instagram card news, and Naver blog strategy
/plugin install gshorts@godsenal
```

A machine that runs content bots needs `gshorts@godsenal` installed too; otherwise its sessions never load the gshorts rules. `scripts/gbase-run` loads gshorts from its checkout for the `content` slot on its own.

Or browse interactively with `/plugin` and go to the **Discover** tab.

## Plugins

### gbase

Core productivity tools for Claude Code — skill discovery, autonomous branch/PR workflows, and backward-compat deploy-order checks.

> **출력 언어:** 모든 gbase 스킬은 사용자에게 보이는 텍스트(진행 보고, 리포트 표, `AskUserQuestion` 질문·옵션)를 **한국어**로 낸다. 코드·경로·명령어·고정 라벨(`critical`, `PASS`/`FAIL`, `✅`/`⚠️`)은 영어 그대로, 커밋 메시지·브랜치 이름은 대상 레포의 기존 관례를 따르고, PR 제목·본문은 기본 한국어로 쓴다(섹션 제목은 영어, 레포가 분명히 다른 언어로 PR을 써 왔으면 그 언어). 다른 언어로 요청하면 그 언어를 쓴다.

**find-skills** — Discover and install Claude Code skills matching your project's tech stack.

- Auto-analyzes `package.json` and `CLAUDE.md` to detect your stack
- Searches local skill repositories and online marketplace
- Recommends skills ranked by relevance
- Handles installation with proper agent scoping

**branch-pr** — Automate branch creation, intelligent commit grouping, and PR generation from current changes. **Runs fully autonomously** — invoking it is the go-ahead to branch, commit, push, and open the PR without step-by-step confirmation.

- Analyzes current git changes
- Decides the branch name and commit grouping itself (by layer, feature, or change type) — no "confirm?" prompts
- Runs the PR title and body through `gbase:unslop`
- Pushes and opens a PR whose body is a reviewer briefing — **Why** (one sentence), **Review focus** (right under it: a GitHub `[!IMPORTANT]` box with the count of what a person must judge and up to five items, each a bold question plus where and why — product/design calls, evidence or high-risk lines no check can judge, and medium+ review findings the diff introduced; a `[!NOTE]` box says plainly when there are none. Below it one line of risk tier · one-way/two-way door · how to undo, and low or pre-existing review findings folded into `<details>`), **Change outline** (a diff sketch of the shape that changed, not a changelog; long parts folded into `<details>`), **Evidence** (before → after, plus the checks already run), rollout order when compat-check flags one, and optional **Notes**. Combines humanlayer `visual-pr`, Matt Pocock's `pr`, Anthropic's code-review write-up, and gbase's own risk/rollout. Each view and evidence pair uses the form that shows that kind of change best — before/after screenshots for UI, a GIF for interaction, a mermaid sequence diagram for cross-component flow, a pseudocode diff plus fail→pass test for logic, a JSON diff for contracts, one number for performance. A UI change ships with its screenshots in the body (a local path doesn't count); they come from the run's `verify-*` or `behavior:` captures and are uploaded to a separate `gbase-assets` branch (never the PR branch). Fills the repo's own PR template instead when one exists
- Calls **compat-check** before opening the PR; injects a `## Rollout / Deploy order` section when a sequenced rollout is needed
- Stops only for the narrow "ask only when necessary" cases: a secret in the diff, unrelated WIP mixed in, an ambiguous PR split, a diverged branch, or remote ambiguity
- Keeps the destructive-command guardrails (no `git reset --hard`, no plain `--force`) and a persistent backup stash

**compat-check** (skill, model-invocable) — Scan a change for backward-compatibility hazards and get the safe deploy/script order.

- Packaged as a Skill (`plugins/base/skills/compat-check/SKILL.md`); read-only — never edits code, runs scripts, or deploys
- Reads a diff (uncommitted, a commit range, or a PR) and flags **migrations** (column drops, `NOT NULL` without default, type narrowing), **API/contract** changes, **queue/event schema** changes, new required **env/secrets**, **feature flags**, **backfill scripts**, **cache/serialization** format changes, **mobile client version skew** (old app versions still in the wild), and **native changes** that can't ship over OTA
- Emits a one-line verdict (`✅ No special deploy ordering needed` or `⚠️ Requires ordered rollout`) and, when needed, a numbered runbook (expand → migrate → backfill → deploy → ramp → follow-up contract PR) with a rollback note, each hazard mapped to `file:line`
- Auto-invoked by **branch-pr** / **go** to drop a `## Rollout / Deploy order` section into the PR body; also runs standalone via `/gbase:compat-check`

**bug-fix** (skill, model-invocable) — Fix a bug at its root cause, not where it surfaced. Ported from pstack's `principle-fix-root-causes` + `bug-fix` playbook (with `tdd` and `attack-the-premise` folded in).

- Reproduces first with **reproduce** (a command that fails now, on the failing surface)
- Narrows the cause by ruling out hypotheses with runtime evidence; every shipped line must trace to that evidence
- Before adding a guard, asks whether the triggering state is legitimate — guards, retries, raised timeouts, and swallowed errors are flagged as the usual ways to hide a bug; fixes every instance of the pattern
- Failing regression test first (only when cheap), shown failing-then-passing in the PR's Evidence — not as a separate red commit, which pre-commit hooks, per-commit CI, and squash merges all defeat; two failed fixes on one premise → stop and test the premise
- Asked only *why* something broke, it stops at the diagnosis; it suggests `/gbase:go` but never ships on its own

**reproduce** (skill, model-invocable) — Turn a bug report or an improvement request into an executable check that fails right now; never changes product code.

- Bug → the repo's own test when a cheap test path exists (it becomes the regression test), else a script, `curl`, CLI run, or a journey through the repo's verify skill
- Improvement request → a criterion the requester would accept, measured now and asserted against the target, so it fails with the current value in its output
- Reports the command, the quoted failing lines, and the expected result; the check must fail *for the stated reason* (an import error or a refused connection is a broken check), run twice for stability, and production is read-only
- `bug-fix` starts with it; with `AGENT_EVIDENCE_FILE` set it appends a `reproduce` evidence line

**mockup** (skill, explicit only) — For a 시안 or design option, a clickable HTML mockup instead of a description. Runs only on `/gbase:mockup` or `gbase-run --slot mockup`; `work`, `go`, and the other slots never call it, and the model doesn't invoke it on its own.

- Reads the app's screens, theme tokens, bundled fonts, and real copy first, so the option is judged on the idea and not on a generic look; a token plan and an ASCII wireframe per option go in `notes.md` first, and options differ in structure, not color alone, next to the current screen when one exists
- One self-contained `index.html` (no CDN or remote assets) at real device size; taps and toggles work, every state is addressable as `#<option>-<step>`, and two or three options sit side by side on one page
- PNG per option and step via `chrome-headless-shell` (regular headless Chrome clamps to 500 px wide), checked before reporting; delivered where the user can open it (the local file, or a Tailscale URL for a phone). Never `tailscale funnel` or a public bind
- Saved to `$GBASE_MOCKUP_DIR` (default `~/design-mockups`) as `<app>-<YYYYMMDD>-<topic>-r<N>/`, outside the app repo; a revision is the next round. No copyrighted reference images, secrets, or real user data
- Ends with `mockup:` / `mockup url:` / `mockup shots:` lines, which `gbase-run` reads into `result.json`

**how** (skill, model-invocable) — Explain how a part of the codebase works, with real files and functions. Ported from pstack's `how`.

- Narrow questions are answered directly; a subsystem-wide one fans out 2–4 read-only explorers (Sonnet) on separate angles, then one explainer reconciles them
- Overview → Key Concepts → How It Works → Where Things Live → Gotchas, with a mermaid diagram only where the flow crosses components; also answers "where should this live"

**why** (skill, model-invocable) — Find out why code is the way it is, with citations. Ported from pstack's `why`.

- Anchors on `git blame`, file history, and the PRs behind it, then queries every connected evidence source in parallel — issue tracker, docs, chat, error tracking/observability/analytics MCPs (PostHog counts for two) — one investigator per source
- Every claim is tiered Direct / Supported / Inferred / Speculative / Unknown and phrased to match; "What We Don't Know" and a per-source coverage line are mandatory, and a hypothesis embedded in the question is tested, not confirmed
- Before a change, ends with a Preserve / Change / Avoid / Risk constraint set

**pause** (skill, explicit only) / **pickup** (skill, model-invocable) — Stop cleanly and resume without redoing work. Ported from pstack's `pause-safely` / `session-pickup` playbooks.

- `pause` (`/gbase:pause` only — it commits, so it never auto-triggers) finishes or backs out of the current step and leaves one `wip:` commit whose body is the resume note — intent, what's done and how it was verified, state, next action, gotchas; never commits to the default branch or secret-looking files, never pushes
- `pickup` reads the trail newest-first — the `wip:` commit, the branch's PR, this project's Claude Code transcripts (only this project's), branches other agents pushed — treats it as authoritative, names the resume point, and re-verifies only the claims the next step depends on
- `go` ships unpushed pause commits even on a clean tree, and `branch-pr` soft-resets all of them back into real commits (a hand-written `wip:` commit without the `Intent:` marker is left alone)

**blast-radius** (skill, model-invocable) — What could this change break *outside* the diff? Ported from pstack's `blast-radius`.

- Looks where grep stops: the called library's source at its pinned version (and local patches), execution timing, JSON/DB/wire formats, feature flags, code three hops downstream
- Finds the one fact the change is safe because of and **proves it by running code** — every claim is graded on a 5-step evidence ladder (said so → `file:line` → walked the failure → ran a script → reproduced in the app), and an unproven one is labelled `unproven`
- Deploy-ordering hazards are handed to `compat-check`; read-only on the repo (scratch scripts go to a temp dir)

**work** (skill, model-invocable + session hook) — The front door for a task. Starts on its own for qualifying tasks, or as `/gbase:work <task>`. Modeled on pstack's `poteto-mode`, without its personal style — gbase now covers what pstack was used for, so pstack can be uninstalled.

- **Session hook** (`hooks/session-start.sh`): at startup, resume, clear, and compact it adds the routing rule in `hooks/session-start.md`, which sends qualifying tasks to `work` and specific intents straight to `bug-fix` / `reproduce` / `how` / `why` / `blast-radius` / `go`. Off with `GBASE_SESSION_HOOK=off`; silent under `AGENT_HEADLESS=1` (the caller names each skill). If pstack is installed, turn its hook off (`session hook: off` in `~/.claude/pstack-models.md`) or uninstall it, since both hooks route the same tasks
- Checks first: resumes unpushed `pause` commits via `pickup`, mentions `setup` once if the repo has no verify block, fast-forwards a stale checkout
- Picks one route and copies its steps into the todo list (skipped steps stay as `skip: <reason>`): **Investigation** (`how`/`why`, no code), **Bug** (`bug-fix`), **Feature** (data shape first, small verified units, verify on the real surface), **Refactor** (pin behavior first, subtract before adding, keep only if easier to follow), **Perf** (baseline first, cheapest fix first), **Prototype** (throwaway variants decide, then Feature), **Run until done** (a checkable exit predicate, revert what didn't help)
- Eight core principles (prove it works, verify in small units, smallest change, fix root causes, model the domain, test behavior, explain the number, don't block on reversible work), reply rules (impact first, every claim labelled 확인함/추정/미확인, `unslop` as you write, candor), and subagent rules on gbase's own agent types (`agents/*.md`): `gbase:scout` (read-only, Sonnet; sweeps files, logs, CI output, or transcripts and returns the conclusion with `path:line` evidence) and `gbase:worker` (one self-contained code unit per agent, launched in parallel worktrees when units are independent, proven on the real artifact, never ships)
- Code routes end in `go`: review ∥ polish → verify → PR → monitor, scaled by risk. The route's own surface verification is handed to `go` as `behavior:` lines so it isn't run twice. **Ship gate:** when `work` started on its own and you haven't asked to ship, it asks once before `go` pushes and opens the PR. **Not merged by default** — `--merge` is added only when you ask for it or the project's own instructions (`CLAUDE.md`, memory) say to merge, so a shared/company repo stops at a merge-ready PR

**unslop** (skill, model-invocable) — Rewrite prose to remove AI writing tells. Ported from pstack's `unslop`, with Korean tells (번역투, empty openers and closers, noun-stacked compression, layered honorifics) added. `work` writes replies by its rules.

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
- **Risk-scaled review and behavior check**: classifies the change `low`/`medium`/`high` from the paths it touches (`REVIEW.md`'s always-high paths, or auth/payments/migrations/CI/app config). `low` (docs, copy, tests, flagged additive changes) skips the pre-PR finder and the behavior check — `monitor`'s self-review covers it during the CI wait; `medium` gets `code-review medium` with all low/medium findings sent to one skeptic; `high` gets `code-review high` and a skeptic per finding. Polish runs the same on every tier
- **Launches the built-in `code-review` in a background agent, then runs `/gbase:polish` while it works.** Wrapping it in an agent keeps the two parallel under `claude -p` too, where a forked skill blocks its caller — and running it *before* the PR means fixes land in the initial commits instead of as churn on an open PR with a CI rerun per fix
- Hands the findings to `/gbase:review` for skeptic verification and the clear-vs-ambiguous gate; clear fixes are applied to the working tree, judgment calls are **deferred** and raised after the PR is open
- **Verification gate** — runs the project's *own* lint/typecheck/tests over the changed scope (from the `gbase:setup` verify block in `CLAUDE.md`/`AGENTS.md` when present; a native build only when the block marks it as the repo's sole compile gate because no CI builds the app), plus a **required behavior check** on `medium`/`high` — reused from the `work` route's own surface run when nothing since changed behavior, otherwise the repo's `verify-*` skill for touched features or the cheapest surface run; an unreachable surface is recorded as `behavior: skip — <reason>`, never silently dropped; results land in the PR's `## Evidence` before anything is pushed (polish's check only validates polish's own edits, so a pre-existing failure would otherwise sail into CI). Each check runs once, scoped to the diff, on the tree after review fixes; a failing check is re-run by file or case before the scoped command. Biased toward shipping: pre-existing, flaky, and environment-dependent failures are noted and passed; only a diff-caused failure that resists two mechanical fix attempts stops the flow. `--no-verify` skips it
- Then `/gbase:branch-pr` (backup → branch → grouped commits → push → PR), then `/gbase:monitor --no-review` to babysit CI + reviews until merge
- **The PR still opens without asking.** Exactly two things can stop the flow before the PR exists: a diff-caused verification failure that isn't mechanically fixable, and branch-pr's narrow "ask only when necessary" cases. Everything else is carried and raised afterward
- `--merge` (only when you ask, or the project's instructions say to merge) also merges once CI is green and nothing is outstanding — **asks first when the merge would deploy** (a push-to-main OTA/production workflow the PR's paths don't skip), uses a merge method the repo allows, retargets stacked PRs before the branch is deleted; a check that never started for account/billing reasons merges only if the local verify gate passed
- Inherits all `branch-pr` safety rules — no force push, no hard reset
- The behavior check recognizes both verify-skill layouts: `.claude/skills/verify-<app>/` (from `create-verify`) and `.claude/skills/verify/` (pstack's generator)
- Under `AGENT_HEADLESS=1` a `low` change still gets the pre-PR finder (`code-review low`, one skeptic), and the tail is `monitor --until-settled` instead of the watch-to-merge loop
- Under `AGENT_SHIP_OWNER=orchestrator` it stops after local commits and a PR body draft (no push, PR, image upload, or monitor) — see [Running gbase from an orchestrator](#running-gbase-from-an-orchestrator)

**monitor** (skill) — Subscribe to the current branch's PR and keep it moving until merge/close.

- Packaged as a Skill (`plugins/base/skills/monitor/SKILL.md`)
- Model-invocable — triggers via `/gbase:monitor`, as the tail of `/gbase:go`, or when Claude judges you want a PR watched until merge (auto-triggering only starts the watch loop; ambiguous items still gate through `AskUserQuestion`)
- Resolves the PR via `gh`, sweeps current CI + reviews, then starts a persistent `Monitor` polling every 30s
- Runs one **adversarial self-review** of the PR (`gbase:review`) right after the watch starts — inside the CI wait the PR already pays, so it costs the ship path nothing; findings are skeptic-verified, clear survivors are auto-fixed in their own commits, the rest come back as a severity-ordered report; nothing is posted to GitHub. This is for PRs `go` didn't ship (opened by an earlier session, a teammate, or by hand) — `go` reviews *before* the PR opens and passes `--no-review`. With `--draft`, flips the draft PR to ready once CI is green
- Auto-fixes clear CI failures (lint, format, type, unused imports) and applies clearly-required review comments (suggested diff blocks, typos, dead code)
- Resolves safe merge conflicts (lockfile regeneration, pure-addition merges, whitespace-only) via rebase + `--force-with-lease`; aborts and surfaces anything semantic
- Runs `/gbase:polish` only on edits beyond its auto-apply gate (a change you approved after it asked, a conflict resolution that rewrote logic); mechanical auto-fixes, lockfile regen, and whitespace-only resolutions are committed without it. `review`'s auto-fixes skip it too
- Surfaces testable preview/deploy links (app builds and OTA previews — EAS/TestFlight/Firebase App Distribution — or web previews like Vercel/Storybook/staging) that CI or bots post — inline, with source + commit SHA, deduped — so you know exactly what to click and test (surface-only; it never opens the link or comments back)
- Replies on every inline review comment it touches — `Addressed in <sha>.` for applied items, a one-line reason for declined ones, a "deferred to maintainer" note when waiting on a decision — so reviewers never wonder whether their comment was seen
- **Converges instead of looping** with automated reviewers: pre-existing findings get a one-line reply and no fix, repeats of handled findings are ignored, and after three rounds from the same reviewer it stops auto-applying and asks whether the approach needs rethinking
- Surfaces anything ambiguous (architecture, behavior, design questions, hedged feedback, semantic conflicts) via `AskUserQuestion`
- Stops automatically when the PR reaches `MERGED` or `CLOSED`
- `--until-settled` ends earlier, once the current head's checks and expected review bots have concluded, with one `settle: 수렴 | 미확정 | 사람 필요 @<sha>` line; it waits in short foreground polls (each returns within 5 minutes), gives up 30 minutes into a head, and never merges, rebases, or force-pushes; under `AGENT_SHIP_OWNER=orchestrator` it pushes nothing and reports its local fix commits and a refreshed PR draft

**setup** (skill, model-invocable) — Prepare a repo for the ship loop in one pass; idempotent, one confirmation.

- Fetches first and offers to fast-forward a stale checkout and install missing dependencies — detecting on old code reports old CI and commands
- Records the project's verify commands (lint/typecheck/test/format, scoped variants, CI-only, known-failing, tests that fail only in the full run, local-vs-CI runtime differences) in a marker block in `CLAUDE.md` — or `AGENTS.md` when that's the repo's only instruction file — **each command is run once before it's recorded**; anything it couldn't run is marked `unverified locally`, so `go` never trusts a command that doesn't work
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

### Running gbase from an orchestrator

A program that runs agents with no person attached (e.g. `claude -p` from a daemon) can slot gbase skills into its own steps. The contract is environment variables, files, greppable report lines, and a manifest; with none of the variables set, every skill behaves as it does interactively. Full spec: [`plugins/base/references/orchestrator.md`](plugins/base/references/orchestrator.md).

| Variable | Effect |
|---|---|
| `AGENT_HEADLESS=1` | No skill asks. It applies its recommendation (or the reversible option that does less) and reports a `결정 필요:` line; irreversible steps (merge, deploy, force push, data deletion) are not taken. Rules: [`references/headless.md`](plugins/base/references/headless.md) |
| `AGENT_ASK_CMD` | Under headless, each question goes to `sh -c "$AGENT_ASK_CMD \"\$@\"" ask "<question>" --recommend "<option>" --option "<option>"…`; non-empty stdout is the answer |
| `AGENT_SHIP_OWNER=orchestrator` | `go` stops after local commits and a PR body draft; `monitor --until-settled` commits its fixes locally and refreshes that draft. Neither touches the remote |
| `AGENT_SHIP_OWNER=agent` | `go` pushes, opens the PR and reports `pr: <url>`; under headless it then runs `monitor --until-settled` and ends with the `settle:` line instead of watching to merge. Never merges |
| `AGENT_PR_BODY_FILE` | Where that draft goes (line 1 title, line 2 empty, then the body); default `$(git rev-parse --absolute-git-dir)/gbase/pr-body.md` |
| `AGENT_EVIDENCE_FILE` | `go`, `reproduce`, and `monitor --until-settled` append `{"step","result","command","detail","cause"?}` JSON lines (`review`, `polish`, `checks`, `behavior`, `reproduce`, `settle`); `result` is `pass`, `fail`, `skip`, or `open` (findings or a wait still open, not a failure) |

The manifest [`plugins/base/.claude-plugin/factory.json`](plugins/base/.claude-plugin/factory.json) maps slots (`work`, `review`, `review2`, `polish`, `checks`, `behavior`, `ship`, `settle`, `learn`, `content`, `task`, `reproduce`, `mockup`) to an invocation, the variables it reads, and notes. `review2` runs `gbase:review` in report-only mode on Opus and Sonnet at once and merges the two tables, marking each finding `opus`, `sonnet`, or `both`. `content` runs gshorts' `content-common` with the format the request names; `task` runs a one-off prompt with no skill (research, a schedule change) so it still leaves a log and `result.json`. `scripts/check.py` checks that every slot names a real skill and that every skill that can ask points at the headless rules.

**Runner.** [`scripts/gbase-run`](scripts/gbase-run) runs one slot headless from a checkout of this repo and writes a `result.json` a poller can read.

- **Who:** a bot or daemon that starts Claude Code with no person attached (the content bots, the dev bots). A person in an interactive session types `/gbase:work` instead.
- **When:** every Claude Code call such a bot makes: `--slot work` for a repo change, `--slot content` for gshorts content, `--slot task` for anything else (research, a schedule change) — never a bare `claude -p`.
- **Why not `/gbase:work` in a bare `claude -p`:** that call has no headless variables (a question hangs), no worktree from origin (it builds on whatever branch is checked out), no `result.json`, `stop`, or lesson handoff, and leaves the bot no way to know it finished.

```
scripts/gbase-run --repo ~/code/app --slot ship --task "로그인 500 수정" --worktree login-fix
scripts/gbase-run --repo ~/code/app --slot work --task "T-12" --worktree t12 --ship-owner agent   # push·PR까지, result.json pr_url
scripts/gbase-run --repo ~/code/app --slot review2
scripts/gbase-run --repo ~/LTH/insta --slot content --task-file task.md   # 긴 작업은 파일로; 교훈: 줄이 있으면 next: 줄로 work 런 명령을 출력
scripts/gbase-run --repo ~/code/app --slot work --task-file rules.md --worktree rules --exclusive   # 같은 레포의 앞선 런이 끝날 때까지 대기
scripts/gbase-run --answers answers.json        # 이전 실행의 결정 필요: 줄에 답하고 이어서 실행
scripts/gbase-run status <run-id>               # 진행 중이면 "status": "running"
scripts/gbase-run stop <run-id>                 # claude와 그 하위 프로세스까지 종료
scripts/gbase-run list
```

It sets `AGENT_HEADLESS=1` and the other variables (ship owner `orchestrator` by default, so nothing is pushed), loads gbase (plus the plugin a slot names, like gshorts for `content`) from the checkout with `--plugin-dir`, blocks `ScheduleWakeup`/`CronCreate`, starts a `--worktree` branch from `origin`'s default branch (or `--base`) rather than the checkout's current branch, removes `GITHUB_TOKEN` from the child, and prints the `result.json` path as its last line. `pr_url` is the PR an agent-owned run opened (for `settle`, the branch's PR). Another run still going on the same repo (matched by origin URL, so two clones count as one) is warned about and listed in `concurrent`; `--exclusive` waits for it. `교훈:` lines from a content run land in `lessons` and `lessons.md`, with a `next:` command for the `work` run that ships them. `decisions` in `result.json` are parsed `결정 필요:` lines (`{text, question, applied, recommend, options, human}`). Since the plugins and `factory.json` come from that checkout, keep the checkout on `origin`'s default branch. A checkout left on an old feature branch runs that branch's skills and slots, regardless of the installed version (one on a 1.32.0 branch had none of the 1.34.0 runner options). Run directory layout, the `result.json` fields, and the answers file format: [orchestrator.md § Runner](plugins/base/references/orchestrator.md#runner).

### gapp

App-building harness — takes a raw app idea all the way to an App Store submission, one skill per stage. Every stage reads/writes `docs/HARNESS.md` (a living pipeline document), and every stage **auto-continues into the next one** unless the user says stop — you should never wonder "what do I run now". Distilled from shipping a real Expo + Supabase app (somandlee) end to end. Delegates to best-in-class skills when installed (gstack `office-hours` for idea validation, gstack `design-consultation` + taste skills for design) instead of reimplementing them.

> **출력 언어:** 모든 gapp 스킬은 사용자와의 대화(진행 보고, 판정 표, `AskUserQuestion`)를 **한국어**로 낸다. 단 **앱 산출물**(앱 UI 문구, 랜딩 카피, 개인정보/지원 페이지, 스토어 메타데이터)은 대화 언어가 아니라 `kickoff`에서 정한 **앱 언어**(`docs/HARNESS.md`)를 따른다. 코드·명령어·워크플로 YAML·상태 라벨은 영어 그대로, PR 제목·본문은 기본 한국어(레포가 분명히 다른 언어로 PR을 써 왔으면 그 언어).

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

### gshorts

Korean content harness: faceless short-form videos for YouTube Shorts, Instagram Reels, and TikTok, plus Instagram card news and Naver blog strategy. The skills hold the format the user has confirmed, feedback by feedback, and point at an external render pipeline (`tiktok-automation`) for the actual commands. They never ship code, keys, or account credentials.

| Skill | What it does |
|---|---|
| **content-common** | Rules for every piece of content: names, bios, captions, cards, and scripts are written from high-performing references actually opened on the target platform, numbers, schedules, or scope from neither references nor the user are reported as `가정:` lines and kept out of public copy until confirmed, public copy carries no source credits and reads as one person's own first-hand writing (sources stay in the work report), opening lines start from hook-templates, text posts put the key numbers in the root, and every mistake or lesson is reported the same turn so other bots don't repeat it. Operations: a post counts as published only when the logged-out public view shows it, automated likes, follows, replies, or link comments start only after the platform's official policy is read and quoted, and causes are reported as `가설:` while operating rules change only on confirmed facts. Holds the **feedback intake**: each new piece of feedback is classified as content-wide, video-wide, or format-specific and reported, dated, as a `교훈:` line for that skill; a content run never edits the harness source, and a `gbase:work` run (the runner's `next:` line) ships the lines as a PR |
| **hook-templates** | 25 Korean first-line hook templates from a high-performing X post (source and metrics kept), per-platform notes (lighter on X, keyword first on Naver blog titles), and the 머니알림 rules: which templates fit, 6 "현직 OO" and 18 "상위 1%" banned, experience hooks (1, 3, 9, 17, 24, 25) only on a real case, no repeating a template in consecutive posts. Every content skill reads it at its hook step |
| **shorts-common** | Rules every short follows (five posts a day with one fixed show per clip slot, length, pacing, audio mix, narration, captions, checks, posting gate — never schedules without the user's OK), and options decided from 2–3 side-by-side samples. Ships a dated trend reference with sources |
| **foreign-clip-short** | Official foreign show clips in framing D (black 9:16 canvas, fixed two-line title, ~1080×930 center crop, Korean subtitles), with per-show variants for the fixed daily series: Antiques Roadshow, Pawn Stars, Shark Tank / Dragons' Den, Kitchen Nightmares, and Undercover Boss as the spare |
| **top3-compilation-short** | Starter for ranked TOP3 compilations. Only the request for the format is confirmed, so the open parts are marked TODO and settled by sample comparison |
| **instagram-card-news** | Instagram card news (carousels) for an info account: references opened before any card, no forced or image-less cards, names patterned on real Korean info brands, no sourcing route or AI tone in the bio, no promises without a setup behind them, mascot picked from samples, posts only after the user's OK |
| **naver-blog** | Naver blog strategy, diagnosis, post template, titles, and monetization order (애드포스트·체험단·쇼핑커넥트) from blogs that rank in 통합검색 now or publicly disclose revenue, opened on mobile Naver first (how to read post bodies, blog stats, cadence via the post-list API, AdPost slots). Diagnosis compares blog-level facts (이웃, 방문, category spread, 블로그 주제, operator identity) before post length or images, never invents an operator, and quotes official thresholds with a check date. Writing a single post stays with the caller's own skill |

## Usage

After installation, the following are available:

```
/gbase:find-skills             # Discover skills for your project (command)
/gbase:branch-pr               # Autonomous branch + commit + PR from current changes (command)
/gbase:compat-check [range]    # Flag backward-compat hazards + emit a deploy-order runbook (skill, model-invocable)
/gbase:polish                  # Two-pass diff polish — deslop + structural (skill, model-invocable)
/gbase:bug-fix                 # Fix a bug at its root cause — reproduce, narrow, verify on the same surface (skill, model-invocable)
/gbase:reproduce <bug|request> # Turn a bug or request into a check that fails now — command, failing output, expected (skill, model-invocable)
/gbase:mockup <request>        # Clickable single-file HTML mockup + screenshots, outside the repo (skill, explicit only)
/gbase:how                     # How does X work — explained with real files (skill, model-invocable)
/gbase:why                     # Why is X this way — cited from git, PRs, and connected sources (skill, model-invocable)
/gbase:pause                   # Stop cleanly with a wip commit whose body is the resume note (skill, explicit only)
/gbase:pickup                  # Resume from a wip commit, transcript, or another agent's branch (skill, model-invocable)
/gbase:blast-radius            # What could this break beyond the diff — proven by running code (skill)
/gbase:review                  # Adversarial review — built-in code-review + skeptic verify (skill, model-invocable)
/gbase:work <task>             # Start a task: route → steps → go (merges only if asked) (skill, model-invocable + session hook)
/gbase:unslop                  # Remove AI writing tells from prose, Korean included (skill, model-invocable)
/gbase:go                      # Review ∥ polish → verify → branch + commit + PR → monitor (skill)
/gbase:monitor                 # Watch current branch's PR — auto-fix clear CI/review items (skill)
/gbase:monitor --until-settled # Stop once this head's CI and review bots have concluded; never merges (skill)
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

/gshorts:content-common        # Rules for every piece of content + feedback intake (read first)
/gshorts:hook-templates        # First-line hook templates + 머니알림 rules
/gshorts:shorts-common         # Every-video rules
/gshorts:foreign-clip-short    # Foreign show clip short (Shark Tank, Pawn Stars, Kitchen Nightmares …), framing D
/gshorts:top3-compilation-short  # TOP3 compilation starter (TODO parts settled by samples)
/gshorts:instagram-card-news   # Instagram card news (carousel) for an info account
/gshorts:naver-blog            # Naver blog strategy, diagnosis, and post template from ranking blogs
```

## License

MIT
