---
name: review
description: "Adversarially reviews the current change for defects (bugs, regressions, security holes, missing handling): skeptic sub-agents try to refute each finding, clear survivors are fixed, the rest reported. Local-only. Use when asked to review a change or find bugs before shipping ('리뷰해 줘', '버그 찾아 줘', '보안 구멍이나 회귀 봐 줘'); also inside gbase:go and gbase:monitor."
allowed-tools: Bash Read Edit Write Glob Grep AskUserQuestion Agent Skill
---

# /gbase:review

Finding is delegated to the built-in `code-review`. This skill adds the judgment: make every finding survive an adversary before it reaches the user, then decide what may be fixed without asking.

Not polish — cleanup (reuse, dedup, clarity) is `gbase:polish`'s job. Not a GitHub actor — no comments, reviews, replies, or merges, ever.

## 출력 언어

사용자에게 보이는 글은 **한국어**로 쓰고, 코드·명령·상태 라벨·커밋·브랜치는 레포 관례를 따른다. 세부: [output-language.md](../../references/output-language.md).

## Headless

Before any `AskUserQuestion`, check `printenv AGENT_HEADLESS`; when it prints `1`, follow [headless.md](../../references/headless.md) instead of asking.

## Scope and mode

Target: explicit paths / range / PR from the caller; else uncommitted changes; else the latest commit. Skip pure renames, dependency bumps, and generated code.

Mode decides how fixes land:

| | **Pre-PR** (from `gbase:go`, or a dirty tree) | **Post-PR** (clean tree + open PR, e.g. from `gbase:monitor`) |
|---|---|---|
| Fixes land as | working-tree edits, no commits — `branch-pr` groups them | one commit per fix, pushed — not pushed under `AGENT_SHIP_OWNER=orchestrator` |

The caller's stated mode wins. Without one, a dirty tree means pre-PR even if a PR is open — committing would sweep the user's unrelated edits into a review commit.

## Repo rules

If the repo has a `REVIEW.md` (root or nearest ancestor of the changed files), it governs every stage: hand it to the finder and each skeptic, drop findings on its skip paths, apply its severity overrides and nit cap. Also flag code that breaks a convention `CLAUDE.md` states, and note when `CLAUDE.md` itself contradicts the code.

## Tests in the target

When the target adds or changes a test file, read [tests.md](references/tests.md) before Stage 2, also when the caller starts you at Stage 2: each of those tests is judged against two imagined edits, and one that fails either joins the candidates. Started at Stage 2 with no scope named, the target is what the caller's findings were found on: the uncommitted changes, else every commit the branch has that its base lacks, not only the latest one. No test file in the target → skip this; nothing is read and no agent is added.

## Stage 1 — Find

If the caller handed in findings (`gbase:go` passes `candidates already found — start at Stage 2`), skip to Stage 2. Otherwise:

```
Skill(skill: "code-review", args: "medium <target>")
```

In the same message, when `codex` is on PATH and the risk is not `low`, start a second finder from another vendor in the background: `codex exec -s read-only review --base <base>` (or `--uncommitted` for a dirty tree), its default prompt unchanged. Its findings join the built-in's as candidates, merged by `file:line`, and go through Stage 2 like any other. Don't wait past the built-in by more than a few minutes; a codex that fails or isn't logged in is skipped with one line in the report. Say which finders ran in the tally line.

- If `code-review` didn't run (unavailable, or you reviewed inline), say so in the tally line; a review that silently skipped its finder reads like a clean one.

- Always pass the target. With none, the built-in reviews the current diff — empty on the clean-tree path, so it reports "nothing found" about a commit it never read.
- `medium` unless the user asked for depth; above it the built-in fans out to a multi-agent workflow at many times the cost, and Stage 2 already removes most of what the extra coverage adds.
- Never `--fix` (bypasses Stage 3), `--comment` (posts to GitHub), or `ultra` (user-triggered and billed — tell the user they can run `/code-review ultra` themselves).
- Drop reuse/simplification/efficiency findings — they're polish's, carry no failure scenario, and would otherwise pass the auto-fix gate and undo restructurings polish chose not to make. Mention them as "noted"; never count or auto-apply them.

If the built-in isn't available, review inline for correctness, error handling, and security across every changed file plus the surrounding code it interacts with; on a larger diff, split the work across parallel sub-agents on the session's model — finding is where model strength buys recall. Every finding needs a concrete failure scenario at `file:line`. Treat these as unverified.

## Stage 2 — Adversarial verify

A skeptic sub-agent must try to refute each finding before it's reported or fixed. Only a `CONFIRMED` finding that will merely be reported (not auto-fixed, not high/critical) skips this — the built-in's own verify is a single non-adversarial pass.

Skeptic prompt (its first line is always `Rules: <path to REVIEW.md>` when the repo has one, and the skeptic reads it before judging):

> Claimed defect: `<finding>` at `file:line`, failure scenario `<scenario>`. Try to refute it: find a concrete reason the scenario can't happen — a guard upstream, an invariant, a dead branch, or every existing caller unable to pass that input — and cite it as `file:line`. Refute the scenario exactly as stated, not a weaker one. Judge code this diff adds by its own contract: what a caller passing anything its signature and the runtime allow (every platform, host, screen size, locale and time zone the app ships to) would get, even if nothing calls it yet; "no caller yet" refutes only code the diff marks unfinished (a TODO or ticket note, mock data, a fixed return, a commit saying a later PR fills it). "It keeps the previous behavior" refutes nothing when the diff itself writes that behavior. Answer `refuted` with the cited reason, `real`, or `ask` only when the answer lives outside the code and the runtime — a product decision or a server contract — with the one question to ask. A runtime fact you couldn't check (what a host, device, or library actually returns) is not a question for the author: if the code allows the failing value, it is `real`. A refutation you can't cite is not a refutation: answer `real`.

One skeptic per low/medium finding — or, with more than ~5 of them, batch 2–3 unrelated findings per skeptic so a large review doesn't spawn a dozen agents; each finding still gets its own verdict. These run with `model: "sonnet"`. High/critical (data loss, security, corruption, crash on a common path) gets three skeptics of its own with different angles, on the session's model, with `model: "opus"` when the session runs Sonnet or Haiku — a wrong refutation silently drops a real bug; a majority refutation kills it. Before launching that panel, read [proven.md](references/proven.md): one of the three tries to prove the finding with a run, and not being able to run it is not a refutation. A model the user names for either tier wins. Refuted findings are dropped from the report; keep the count and one-line reasons. `ask` findings are never auto-fixed: list them after the table as `ask: file:line — finding — question`, outside the `S survived` / `K for you` counts, so the PR body can carry the question to the author.

When the caller says *one skeptic for low/medium* (`gbase:go` does on a medium-risk change, and on a low-risk one when headless), all low/medium findings go to a single Sonnet skeptic, each still judged separately; high/critical keep their panel. The skeptic stays a separate agent — the caller already holds the finder output and would anchor on it.

## Stage 3 — Act

**Pre-existing first.** If the defective line isn't in the diff's added/changed hunks (check `git blame` against the base when unsure), label it `pre-existing`: report it, never auto-fix it, and keep it out of the `S survived` / `K for you` counts (it still gets its own table row). Fixing it widens the PR beyond its intent and pins an old bug on this change.

**Fix the class, not the line.** When a survivor is a pattern (a missing `await`, an unchecked `null`, a wrong unit), grep the diff for every other instance and treat them as one finding — otherwise the next round finds the sibling.

**Auto-fix** a survivor only when the fix is mechanical, local (one or two files, small), and fully determined by the finding — no design choice, dependency, schema/migration, API-contract change, or test added/removed. Land it per the mode, without re-running `gbase:polish` — the gate already limits it to a mechanical, local edit.

When the caller says *report only* (the orchestrator's `review2` slot runs two reviewers on one tree at once), auto-fix nothing: every survivor goes in the report as `needs decision`, so neither reviewer edits under the other.

**Everything else** goes in the report; raise the ones worth fixing before merge with `AskUserQuestion` (`file:line`, failure scenario, 2–3 options). When the caller says *defer, don't ask* (`gbase:go` does, so nothing blocks the PR), return them instead of asking.

If the PR merges before a fix lands, don't push to the merged branch — report it as a follow-up.

## Report

Severity-ordered table `# | severity | file:line | finding | action (auto-fixed / needs decision / pre-existing / noted)`, its header in English as written, since `gbase-run` parses it and drops a row it can't read. `severity` must be `critical`, `high`, `medium`, or `low`: the built-in's `important` is `high` or `critical` when it fits Stage 2's high/critical (data loss, security, corruption, crash on a common path), else `medium`, and `nit` is `low`. A raw label left in is read only by `gbase-run`'s fallback for an older review (`"important": "medium"`, `"nit": "low"`), which ranks every `important` as medium. Then the tally line `review: F found, R refuted, S survived — A auto-fixed, K for you`. Optionally one line on the sharpest refuted candidate.

## Safety

- No `git reset --hard`, `git checkout .`, `git clean -f`, plain `git push --force`, `git stash drop`.
- Undo a bad auto-fix by reversing your own `Edit`, never `git checkout --` / `git restore` — in pre-PR mode the whole change is uncommitted.
- A bug too entangled to fix mechanically is reported, not half-fixed.
