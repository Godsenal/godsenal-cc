---
name: setup
description: "Prepares a repo for the gbase ship loop — records the project's own verify commands in CLAUDE.md or AGENTS.md (after running each once on current code), seeds a short REVIEW.md that gbase:review follows, adds a formatter hook, and offers a project-local verification skill. Idempotent; writes only after one confirmation. Use when starting to use gbase in a repo, when gbase:go couldn't find the project's checks, or on /gbase:setup."
allowed-tools: Bash Read Write Edit Glob Grep AskUserQuestion Skill
---

# /gbase:setup

Gives the repo what `go` / `review` / `monitor` otherwise re-guess every run: which commands prove a change, what counts as a defect here, and what to skip.

## 출력 언어

사용자에게 보이는 텍스트는 **한국어**로 쓴다 — 진행 보고, 요약, 리포트 표의 설명 칸, 집계/tally 라인, `AskUserQuestion`의 질문·헤더·옵션·설명까지 전부. 하위 에이전트를 띄울 때도, 결과가 사용자에게 그대로 노출되는 텍스트는 한국어로 돌려달라고 프롬프트에 적는다.

영어 그대로 두는 것: 코드·식별자·파일 경로·명령어·스킬/툴 이름, 고정 라벨과 상태 키워드(`critical`/`high`/`medium`/`low`, `PASS`/`FAIL`, `✅`/`⚠️`), 그리고 커밋 메시지·브랜치 이름 — 이건 레포의 기존 관례(`git log`)를 따른다. PR 제목·본문은 기본 **한국어**로 쓴다 — 섹션 제목 같은 템플릿 라벨은 영어로 두고, 레포가 분명히 다른 언어로 PR을 써 왔거나(예: 영어 오픈소스) 사용자가 요청하면 그 언어를 따른다. verify 블록과 `REVIEW.md` 본문은 레포 문서의 기존 언어를 따른다.

사용자가 다른 언어로 요청하면 그 언어를 따른다.

## Headless

Before any `AskUserQuestion`, check `printenv AGENT_HEADLESS`; when it prints `1`, follow [headless.md](../../references/headless.md) instead of asking.

## What it writes

All four are optional. Ask at most two questions: one before detecting, only if a prerequisite is missing (a checkout behind its upstream, uninstalled dependencies), and one preview to confirm before writing (`AskUserQuestion`: apply all / choose / cancel). *headless:* fast-forward when it is one, install from the lockfile, and apply all — every write stays uncommitted. Never touch content outside the managed markers. On a re-run, update blocks in place and report "no change" when current.

**Detect on current code.** `git fetch` first; if the branch is behind its upstream, offer to fast-forward before detecting — a stale checkout reports stale CI and commands (it has: a repo "with no CI" whose workflows were seven commits ahead). If dependencies aren't installed, offer to install them in the same question; if declined, record the commands as unverified.

### 1. Verify block in the agent instruction file

Target `CLAUDE.md`; if the repo has only `AGENTS.md`, use it and don't create `CLAUDE.md`. If the commands are already listed in one of them (e.g. `CLAUDE.md` imports `AGENTS.md`), put the block where the list is.

Discover commands from those files, `package.json` scripts, Makefile/justfile, `pyproject.toml`, and CI workflows — CI is the ground truth for what must pass. **Run each read-only one once** (lint, typecheck, test, a plain debug compile like `xcodebuild build` / `gradle assembleDebug`) before recording it — a recorded command that doesn't exist or always fails misleads every later `go`. Never run a writing command (`format`, `--fix`, `--write`, codegen, migrate, archive/deploy/upload) during detection; record those unrun. A pre-existing failure is recorded, not dropped. A test that fails in the full run but passes alone is recorded as such — it's flaky *or* order-dependent, so say which you saw; setup never edits product code. If the file already lists these commands, put the markers around that section and normalize it to the block's lines rather than adding a second copy — two lists drift apart.

```markdown
<!-- gbase:verify:start -->
## Verify
- lint: `pnpm lint` · scoped: `pnpm eslint <files>`
- typecheck: `pnpm tsc --noEmit`
- test: `pnpm vitest run` · scoped: `pnpm vitest run <files>`
- format: `pnpm prettier --write <files>`
- CI-only (don't run locally): `eas build`, e2e
- typecheck (no CI): `xcodebuild … build`   ← only when no CI job builds the app
- unverified locally: <command> — <why it wasn't run>
- local vs CI: <runtime difference, e.g. Node 24 here, 22.13 in CI>
- known failing on main: <command> — <reason, date>
- fails only in the full run: <test> — <flaky or order-dependent, date>
<!-- gbase:verify:end -->
```

`gbase:go` reads this block for its verification gate and trusts every line except `unverified locally`. Prefer scoped variants: the gate runs on the changed files. Keep the block to the lines that apply — the file loads into every session. If no pre-commit hook or CI job runs these commands, say so in the report; that's the first gap `gbase:correct` would flag.

### 2. `REVIEW.md` at the repo root

Only if none exists; otherwise propose additions, never overwrite. Keep it under ~20 lines — every review loads it. Build it from repo evidence (domain, sensitive dirs, generated paths, past reverts), not a generic template:

```markdown
# REVIEW.md
Failure here = <what a real defect does in this repo, e.g. "a migration locks a hot table", "a wrong price reaches checkout">.
Always high severity: <auth/, billing/, supabase/migrations/, .github/workflows/>.
Skip: <generated paths, *.snap, lockfiles>.
Cap nits at 3. Every finding needs file:line evidence, not a guess from a name.
```

### 3. Formatter hook

Only when the repo has a formatter configured (prettier, biome, ruff, gofmt, …). Merge into `.claude/settings.json` without clobbering existing hooks:

```json
{"hooks": {"PostToolUse": [{"matcher": "Edit|Write", "hooks": [{"type": "command",
  "command": "f=$(jq -r '.tool_input.file_path // empty'); [ -n \"$f\" ] && <formatter> \"$f\" >/dev/null 2>&1 || true"}]}]}}
```

Restrict the formatter to the file types it handles (`--ignore-unknown` for prettier). The trailing `|| true` matters: a failing hook would surface as an error after every edit. Check `jq` exists; otherwise use a `python3 -c` one-liner.

### 4. Offers (ask, don't push)

- No `.claude/skills/verify-*` or `.claude/skills/verify/` and the repo has a runnable surface (an app, CLI, or service — not a library or docs-only repo) → offer `gbase:create-verify` so `go` can prove behavior, not just types.
- The target file is `CLAUDE.md` and has no Karpathy block → offer `gbase:karpathy` (it writes `CLAUDE.md`, so skip the offer in an `AGENTS.md`-only repo).

## Report

One line per item: `<CLAUDE.md | AGENTS.md> verify block: added | updated | no change`, `REVIEW.md: created | additions proposed | skipped`, `hook: added (<formatter>) | skipped (<reason>)`, plus each command's run result. The files are left uncommitted — say so; `/gbase:go` ships them.
