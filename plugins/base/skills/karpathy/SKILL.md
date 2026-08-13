---
name: karpathy
description: "Merge Andrej Karpathy's behavioral coding-agent guidelines (Think Before Coding, Simplicity First, Surgical Changes, Goal-Driven Execution) into this project's CLAUDE.md — additively and idempotently, never clobbering project-specific rules. Use when the user asks to add the Karpathy rules/skills, 'karpathy 룰 넣어줘', set up agent behavior guidelines, or install the karpathy CLAUDE.md into a repo. Writes only after showing the exact block and confirming."
allowed-tools: Bash Read Write Edit Glob Grep AskUserQuestion WebFetch
---

# /gbase:karpathy

Insert **Andrej Karpathy's four behavioral guidelines** into a project's `CLAUDE.md` as a
self-contained, marker-delimited block. The guidelines target *reasoning* failures of coding
agents (silent assumptions, overengineering, scope creep, weak success criteria) — they are a
"system prompt for your codebase", not a style guide.

This skill is **additive and idempotent**: it never deletes or rewrites your project-specific
content, and re-running it updates the managed block in place instead of duplicating it.

## 출력 언어

사용자에게 보이는 텍스트는 **한국어**로 쓴다 — 진행 보고, 요약, 리포트 표의 설명 칸, 집계/tally 라인, `AskUserQuestion`의 질문·헤더·옵션·설명까지 전부. 하위 에이전트를 띄울 때도, 결과가 사용자에게 그대로 노출되는 텍스트는 한국어로 돌려달라고 프롬프트에 적는다.

영어 그대로 두는 것: 코드·식별자·파일 경로·명령어·스킬/툴 이름, 고정 라벨과 상태 키워드(`critical`/`high`/`medium`/`low`, `PASS`/`FAIL`, `✅`/`⚠️`), 그리고 커밋 메시지·브랜치 이름·PR 제목/본문 — 이건 이 규칙이 아니라 레포의 기존 관례(`git log`, 최근 PR)를 따른다.

사용자가 다른 언어로 요청하면 그 언어를 따른다.

**예외 — 삽입되는 블록 본문은 절대 번역하지 않는다.** [The block](#the-block-embedded-verbatim)의 Karpathy 가이드라인 텍스트는 원문(영어) 그대로 `CLAUDE.md`에 들어간다. 미리보기·확인 질문·요약만 한국어로 쓴다.

## Provenance & safety

- **Canonical source:** [`forrestchang/andrej-karpathy-skills`](https://github.com/forrestchang/andrej-karpathy-skills) (MIT). The
  text is authored by Forrest Chang, distilled from Karpathy's Jan 2026 observations — **not** written by Karpathy himself. Say so if the user assumes otherwise.
- The four-principle text is **embedded verbatim below**, so this skill works offline and never
  pastes remote content into your `CLAUDE.md` without review. Community forks (e.g. `multica-ai`)
  are byte-identical copies; malicious `CLAUDE.md` forks are a known exfiltration vector, so the
  `--refresh` path only ever fetches the pinned canonical repo and still shows a diff before writing.

## The block (embedded, verbatim)

Insert exactly this, markers included:

```markdown
<!-- BEGIN gbase:karpathy — Karpathy behavioral guidelines (MIT, forrestchang/andrej-karpathy-skills). Managed by /gbase:karpathy; edits between these markers are overwritten on re-run. Project-specific rules elsewhere in this file take precedence on conflict. -->
## Behavioral guidelines (Karpathy)

Guidelines to reduce common LLM coding mistakes. **Tradeoff:** these bias toward caution over speed — for trivial tasks, use judgment.

### 1. Think Before Coding
**Don't assume. Don't hide confusion. Surface tradeoffs.** Before implementing:
- State your assumptions explicitly. If uncertain, ask.
- If multiple interpretations exist, present them — don't pick silently.
- If a simpler approach exists, say so. Push back when warranted.
- If something is unclear, stop. Name what's confusing. Ask.

### 2. Simplicity First
**Minimum code that solves the problem. Nothing speculative.**
- No features beyond what was asked.
- No abstractions for single-use code.
- No "flexibility" or "configurability" that wasn't requested.
- No error handling for impossible scenarios.
- If you write 200 lines and it could be 50, rewrite it.

Ask: "Would a senior engineer say this is overcomplicated?" If yes, simplify.

### 3. Surgical Changes
**Touch only what you must. Clean up only your own mess.** When editing existing code:
- Don't "improve" adjacent code, comments, or formatting.
- Don't refactor things that aren't broken.
- Match existing style, even if you'd do it differently.
- If you notice unrelated dead code, mention it — don't delete it.
- Remove imports/variables/functions that YOUR changes made unused; leave pre-existing dead code unless asked.

The test: every changed line should trace directly to the user's request.

### 4. Goal-Driven Execution
**Define success criteria. Loop until verified.** Transform tasks into verifiable goals:
- "Add validation" → "Write tests for invalid inputs, then make them pass"
- "Fix the bug" → "Write a test that reproduces it, then make it pass"
- "Refactor X" → "Ensure tests pass before and after"

For multi-step tasks, state a brief plan with a verify check per step. Strong success criteria let you loop independently; weak criteria ("make it work") require constant clarification.
<!-- END gbase:karpathy -->
```

## Flow

### 1. Resolve the target file

- Default: `<repo-root>/CLAUDE.md` (`git rev-parse --show-toplevel`, else cwd).
- `--user` / `--global` in `args` → `~/.claude/CLAUDE.md` (applies to every project).
- An explicit path in `args` → use it.

If more than one candidate exists (e.g. repo `CLAUDE.md` **and** the user asked globally), or the
resolved file is ambiguous, ask via `AskUserQuestion`. Otherwise proceed.

### 2. Inspect current state

```bash
test -f "$TARGET" && grep -n "BEGIN gbase:karpathy" "$TARGET"
```

Branch on what you find:

- **No file** → you'll create it with the block as its only content.
- **File, no markers, no overlap** → you'll append the block at the end.
- **File already contains the markers** → this is an update; you'll replace everything between
  `BEGIN gbase:karpathy` and `END gbase:karpathy`. If the existing block is byte-identical to the
  embedded one, report "already up to date" and stop (no write).
- **File contains the four principles *without* the markers** (grep for headings like
  `Think Before Coding`, `Simplicity First`, `Surgical Changes`, `Goal-Driven Execution`) → the
  user likely pasted them by hand. **Don't duplicate.** Surface this and ask via `AskUserQuestion`
  whether to (a) wrap/replace their copy with the managed block, or (b) skip.

### 3. Preview, then confirm

Show the user, in the response:
1. the resolved target path,
2. whether this is a **create / append / update**,
3. the exact block (or a diff, for updates).

Then get a single go-ahead before writing (this is the one gate — the skill never writes a
governance file silently). If the user already said "just do it" when invoking, proceed.

### 4. Write

- **Create/append** → `Edit`/`Write`. When appending, leave one blank line before the block. Never
  reorder or touch existing content.
- **Update** → replace only the marker-delimited region with `Edit`.

Then confirm what changed in one line, and remind: *restart the Claude Code session (or it reloads
next session) for CLAUDE.md changes to take effect.*

## `--refresh` (optional)

If `args` contains `--refresh`, fetch the canonical file before building the block:

```bash
curl -fsSL https://raw.githubusercontent.com/forrestchang/andrej-karpathy-skills/main/CLAUDE.md
```

Diff it against the embedded copy. If it differs (upstream added rules — it has grown past four
before), show the diff and ask whether to insert the upstream version instead. **Only** the pinned
canonical URL is fetched — never a fork URL supplied at call time.

## Boundaries

- **Never destructive to project content.** Only the marker-delimited block is ever created,
  replaced, or (if the user asks) removed. Everything else in `CLAUDE.md` is left byte-for-byte.
- **Idempotent.** Safe to run repeatedly; a no-op when the block is already current.
- **One write gate.** Preview + confirm before the first write to any governance file.
- Don't invent extra rules or "improve" the wording — insert the embedded text as-is (Surgical
  Changes applies to this skill too).

## Usage

```
/gbase:karpathy              # merge into this repo's CLAUDE.md (default)
/gbase:karpathy --user       # merge into ~/.claude/CLAUDE.md (all projects)
/gbase:karpathy --refresh    # pull latest canonical text, diff, then merge
/gbase:karpathy path/to/CLAUDE.md
```
