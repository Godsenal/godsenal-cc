---
name: create-verify
description: "Generates a project-local verification skill (.claude/skills/verify-<app>/) that drives the real app the way a user does — web, mobile simulator, CLI, or API — and captures evidence, plus a per-feature map; proves the generated skill by running it once before handing it over. With --maintain, audits an existing verify skill against the current code and live app and fixes drift. Use when a repo has no scripted way to prove behavior, when gbase:setup offers it, or on /gbase:create-verify."
allowed-tools: Bash Read Write Edit Glob Grep AskUserQuestion Agent
---

# /gbase:create-verify

Lint, types, and unit tests prove the code compiles and units behave; they don't prove the feature works. This generates the missing piece: a skill the next agent reads cold, mid-task, to launch the app, drive one feature, and capture proof. `gbase:go` runs it for features the diff touches. Adapted from pstack's `create-verification-skill` / `maintain-verification-skill` (MIT).

## 출력 언어

사용자에게 보이는 텍스트는 **한국어**로 쓴다 — 진행 보고, 요약, 리포트 표의 설명 칸, 집계/tally 라인, `AskUserQuestion`의 질문·헤더·옵션·설명까지 전부. 하위 에이전트를 띄울 때도, 결과가 사용자에게 그대로 노출되는 텍스트는 한국어로 돌려달라고 프롬프트에 적는다.

영어 그대로 두는 것: 코드·식별자·파일 경로·명령어·스킬/툴 이름, 고정 라벨과 상태 키워드(`critical`/`high`/`medium`/`low`, `PASS`/`FAIL`, `✅`/`⚠️`), 그리고 커밋 메시지·브랜치 이름·PR 제목/본문 — 이건 이 규칙이 아니라 레포의 기존 관례(`git log`, 최근 PR)를 따른다. 생성되는 `verify-<app>` 스킬 본문은 에이전트용이므로 영어로 쓴다.

사용자가 다른 언어로 요청하면 그 언어를 따른다.

## 1. Interview the repo, not the user

Answer from the codebase; ask only what can't be observed (test account credentials, a paid entitlement).

- **Surface** — what a user touches: web UI, mobile app, CLI/TUI, API. Pick the primary; note the rest.
- **Run** — the repo's own dev command, ports, env, seed data, auth.
- **Drive** — existing harnesses first (Playwright/Cypress specs, Maestro flows, Detox, curl-able endpoints). Only then a generic recipe: Playwright or Chrome MCP for web; for Expo/React Native, a simulator (`xcrun simctl`, deep links via `simctl openurl`, Maestro if installed) — accessibility labels as handles; tmux/PTY for CLIs; plain HTTP for services.
- **Observe** — screenshots, accessibility snapshots, response bodies, logs, exit codes, DB rows.
- **Isolate** — can two instances run side by side? If not, the skill must refuse to drive an instance it didn't start; corrupting the user's dev session is worse than a skipped check.

If the checkout doesn't build or start, fix that or report it precisely first — a skill written against a broken base teaches wrong steps.

## 2. Generate the skill

Write `.claude/skills/verify-<app>/SKILL.md` with frontmatter (`name: verify-<app>`, and a `description` naming the app, surface, and when to use it — without frontmatter it never registers). Sections, each filled from what step 1 found, no placeholders:

- **Launch** — exact command, and how to tell it's *usable* (a health check can pass while migrations still run). Reaches a usable state from empty data, seeds included. Teardown command.
- **Doctor** — one read-only check: process up, right build, port owned by this run, auth valid. Run first, and again after anything surprising.
- **Drive** — the real selectors/commands from this repo. Stable handles (accessibility labels, test IDs, routes, prompt strings) over coordinates.
- **Evidence** — what to capture and where (`artifacts/verify/<feature>/`, gitignored). Proof standards: drive the real user path, not internal setters or test-only endpoints; capture the action *and* the resulting state; check side effects (rows, files, requests) alongside the screen; a dry-run's claims are verified by observation, not by its name.
- **Cleanup** — kill only what this run started, never by process name. Cleanup never deletes evidence.
- **Helpers** — any shipped script is executable and its invocation appears in the body.

## 3. Seed the feature map

`features/README.md` (baseline preconditions, driving conventions, index) plus one file per user-facing feature — the top 3–5 from routes, screens, or commands. Shape: [references/feature-map.md](references/feature-map.md). If seed data lacks a precondition a journey needs, the journey fails and the reason goes in that feature's `Gotchas` — never weaken the journey to make it pass.

## 4. Prove it before handing it over

Run the generated skill end to end once: launch → doctor → drive ONE mapped feature → capture evidence → cleanup → confirm the evidence still exists. Run cleanup after every failed iteration too, so broken attempts don't strand processes or ports. **A generated skill that was never executed is a draft, not a deliverable** — report it as such if the run can't complete.

Add `artifacts/verify/` to `.gitignore`. Leave the skill uncommitted for `/gbase:go`.

## --maintain

A feature map rots as the app changes. Locate `.claude/skills/verify-*/` (several → ask; none → stop and offer create mode).

1. **Index hygiene** — README index vs. feature files: missing, extra, dead entries.
2. **Source wave** — one read-only sub-agent per feature file, in parallel, with `model: "sonnet"` (the live pass re-checks whatever they claim): how the feature works now from source, likely drift with `file:line`, one live recipe. They never drive the app or edit.
3. **Live pass** — required even when source looks clean. The main agent drives every feature at least once, doctor before the first drive and after any failure. An unreachable feature is reported with the missing prerequisite and the route tried.
4. **Triage** — wrong description → fix the map; working behavior the harness can't drive → fix the harness and re-drive it; app actually broken → product regression, report it to the user and **don't paper over it in the map**.

Edit only the verify skill's own directory. Outcome is one of `clean` (no edits), `changed` (list proven corrections), `blocked` (what stopped it).
