---
name: create-verify
description: "Generates a project-local verification skill (.claude/skills/verify-<app>/) that drives the real app (web, mobile simulator, CLI, or API) and proves it by running it once; --maintain fixes drift. Use when a repo has no scripted way to prove behavior, when gbase:setup offers it, or on /gbase:create-verify."
allowed-tools: Bash Read Write Edit Glob Grep AskUserQuestion Agent
---

# /gbase:create-verify

Lint, types, and unit tests prove the code compiles and units behave; they don't prove the feature works. This generates the missing piece: a skill the next agent reads cold, mid-task, to launch the app, drive one feature, and capture proof. `gbase:go` runs it for features the diff touches. Adapted from pstack's `create-verification-skill` / `maintain-verification-skill` (MIT).

## 출력 언어

사용자에게 보이는 텍스트는 **한국어**로 쓴다 — 진행 보고, 요약, 리포트 표의 설명 칸, 집계/tally 라인, `AskUserQuestion`의 질문·헤더·옵션·설명까지 전부. 하위 에이전트를 띄울 때도, 결과가 사용자에게 그대로 노출되는 텍스트는 한국어로 돌려달라고 프롬프트에 적는다.

영어 그대로 두는 것: 코드·식별자·파일 경로·명령어·스킬/툴 이름, 고정 라벨과 상태 키워드(`critical`/`high`/`medium`/`low`, `PASS`/`FAIL`, `✅`/`⚠️`), 그리고 커밋 메시지·브랜치 이름 — 이건 레포의 기존 관례(`git log`)를 따른다. PR 제목·본문은 기본 **한국어**로 쓴다 — 섹션 제목 같은 템플릿 라벨은 영어로 두고, 레포가 분명히 다른 언어로 PR을 써 왔거나(예: 영어 오픈소스) 사용자가 요청하면 그 언어를 따른다. 생성되는 `verify-<app>` 스킬 본문은 에이전트용이므로 영어로 쓴다.

사용자가 다른 언어로 요청하면 그 언어를 따른다.

## Headless

Before any `AskUserQuestion`, check `printenv AGENT_HEADLESS`; when it prints `1`, follow [headless.md](../../references/headless.md) instead of asking.

## 1. Interview the repo, not the user

Answer from the codebase; ask only what can't be observed (test account credentials, a paid entitlement).

- **Surface** — what a user touches: web UI, mobile app, CLI/TUI, API. Pick the primary; note the rest.
- **Run** — the repo's own dev command, ports, env, seed data, auth.
- **Drive** — existing harnesses first (Playwright/Cypress specs, Maestro flows, Detox, curl-able endpoints). Only then a generic recipe: Playwright or Chrome MCP for web; for Expo/React Native, a simulator (`xcrun simctl`, deep links via `simctl openurl`, Maestro if installed) — accessibility labels as handles; tmux/PTY for CLIs; plain HTTP for services.
- **Observe** — screenshots, accessibility snapshots, response bodies, logs, exit codes, DB rows.
- **Isolate** — can two instances run side by side? If not, the skill must refuse to drive an instance it didn't start; corrupting the user's dev session is worse than a skipped check.

If the checkout doesn't build or start, fix that or report it precisely first — a skill written against a broken base teaches wrong steps. When a missing asset the feature doesn't need blocks startup (a static dir the API never serves, a sample config), the generated skill may create it. It marks the asset as verification scaffolding and removes it in cleanup.

## 2. Generate the skill

Write `.claude/skills/verify-<app>/SKILL.md` with frontmatter (`name: verify-<app>`, and a `description` naming the app, surface, and when to use it — without frontmatter it never registers). Sections, each filled from what step 1 found, no placeholders:

- **Launch** — exact command, and how to tell it's *usable* (a health check can pass while migrations still run). Reaches a usable state from empty data, migrations and seeds included. Teardown command. A short-lived CLI or TUI has no server to keep alive: launch builds the binary (or installs deps) once, and each drive starts in its own isolated PTY or tmux session.
- **Doctor** — one read-only check: process up, right build, port owned by this run, auth valid. Run first, and again after anything surprising.
- **Drive** — the real selectors/commands from this repo. Stable handles (accessibility labels, test IDs, routes, prompt strings) over coordinates.
- **Evidence** — what to capture and where (`artifacts/verify/<feature>/`, gitignored). Proof standards: drive the real user path, not internal setters or test-only endpoints; capture the action *and* the resulting state; check side effects (rows, files, requests) alongside the screen; mocks only where a production boundary already isolates the external system; what a dry-run or test mode skips is verified by observation (files, network, git refs), not by its name — some still touch the network or open a browser.
- **Cleanup** — kill only what this run started, never by process name. Cleanup never deletes evidence.
- **Helpers** — any shipped script is executable and its invocation appears in the body.

## 3. Seed the feature map

`features/README.md` (baseline preconditions, driving conventions, index) plus one file per user-facing feature — the top 3–5 from routes, screens, or commands. Shape: [references/feature-map.md](references/feature-map.md). If seed data lacks a precondition a journey needs, the journey fails and the reason goes in that feature's `Gotchas` — never weaken the journey to make it pass.

## 4. Prove it before handing it over

Run the generated skill end to end once: launch → doctor → drive ONE mapped feature → capture evidence → cleanup → confirm the evidence still exists. Run cleanup after every failed iteration too, so broken attempts don't strand processes or ports. **A generated skill that was never executed is a draft, not a deliverable** — report it as such if the run can't complete.

If the run was proved in a stand-in for the real target (a container for a fresh VM, a local stack for a remote one, a simulator for a device), list every setup step the stand-in did that the target won't. Those steps stay unverified until a run on the real target covers them.

Add `artifacts/verify/` to `.gitignore`. Leave the skill uncommitted for `/gbase:go`, and tell the user `/gbase:create-verify --maintain` keeps the map honest as the app changes (a cadence only if they ask).

## --maintain

A feature map rots as the app changes. Locate `.claude/skills/verify-*/` or `.claude/skills/verify/` (several → ask, *headless:* each in turn; none → stop and offer create mode).

1. **Index hygiene** — README index vs. feature files: missing, extra, dead entries.
2. **Source wave** — one read-only sub-agent per feature file, in parallel, with `model: "sonnet"` (the live pass re-checks whatever they claim): each returns a feature summary, source entry points, likely drift with `file:line` (or none), and one live recipe. They never drive the app or edit.
3. **Reconcile** — every feature file has a returned summary. Merge overlapping recipes into as few app states as practical; spot-check cited drift, don't re-prove clean claims. Sweep recent commits for user-facing surfaces the map lacks, and call one missing only with a concrete source path.
4. **Live pass** — required even when source looks clean. The main agent drives every feature at least once, following the skill's own Launch model. These hold whatever fails:
   - Never drive an instance that hasn't passed doctor since it last surprised you: doctor before the first drive, on each fresh session, and after any failed drive. Where doctor can't see the failure (a wedged UI on a healthy process), reset to a known state or relaunch.
   - Evidence captured so far survives every cleanup — checked at its named location, not assumed.
   - Nothing a drive started outlives its use: failed-iteration residue is cleaned whether the session is stuck, exited, or shared (on a shared instance, clean the residue, not the instance). Final teardown comes after the last drive, re-proofs included.
   - A doctor failure caused by skill drift is a drift finding: fix it, restart only what the fix invalidated, and retry once. Call the pass `blocked` only if it still fails.
   - A feature is `verified-unreachable` only with the concrete prerequisite (auth, entitlement, OS, external state) and the route tried. A prerequisite the map omits is itself drift.
5. **Triage** — wrong or missing user-POV description → fix the map; working behavior the harness can't drive → fix the harness (same Helpers rule as generation) and re-drive it live before it counts; app actually broken → product regression, report it to the user and **don't paper over it in the map**.

Edit only the verify skill's own directory, never product code. Outcome is one of `clean` (every feature got source and live coverage, no edits), `changed` (re-read every changed file, list the proven corrections, and leave them uncommitted for `/gbase:go`), `blocked` (what stopped it). Report the coverage with the outcome. Run notes (features covered, unreachable prerequisites, confirmed drift) stay in a scratch dir, uncommitted.
