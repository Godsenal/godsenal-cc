---
name: polish
description: "Two-pass code polish on the current diff. Pass 1 fans out to three parallel lenses (AI cruft & dead code, code reuse & duplication, clarity & efficiency), then a resolution step dedupes/filters/applies. Pass 2 hunts for ambitious behavior-preserving structural simplifications. Use after writing code, before review, or whenever a diff feels bloated — operates autonomously and proactively right after edits land. The polish role inside `gbase:go` and `gbase:monitor`: unlike the built-in `simplify`, it splits its posture by risk (aggressive on reuse/dedup, conservative on net-new abstraction), gates on a recall checklist, refuses to auto-apply out-of-diff edits, and reverts a failed edit by reversing its own `Edit` rather than `git checkout --`."
allowed-tools: Bash Read Edit Write Glob Grep AskUserQuestion Agent
---

# /gbase:polish

Two polish passes on the current diff (or files the caller hands in). Both passes are **behavior-preserving** — no bug fixes, no contract changes, no API tweaks. If a real correctness bug surfaces during polishing, stop and surface it to the user rather than silently patching it.

Polish runs autonomously and proactively whenever code has just been written or modified — don't wait for an explicit ask once a non-trivial diff exists.

## Posture — asymmetric by risk

Polish is **not uniformly cautious**. A low change-count is a virtue only when it comes from *searching thoroughly and finding little* — never from *not looking*. Split every candidate by risk and treat the two halves differently:

- **Reuse of existing code & literal de-duplication** — calling a helper that already exists, collapsing byte-identical blocks, deleting dead code. **Low risk, high value → be aggressive.** The bar to *leave* such a finding is "I grepped and there genuinely is no helper / no other copy", not "the diff looked fine".
- **Net-new abstraction** — inventing a wrapper, data-driving an explicit list, adding a config array or indirection. **High risk → be conservative.** Prefer the house style; three similar lines beat a premature abstraction.

Reading the repo's conventions (`CLAUDE.md` / `AGENTS.md`) sharpens this rather than overriding it: a codebase that bans "clever" code objects to *new* cleverness, not to reusing what already exists. Don't let an "explicit over clever" culture talk you out of calling an existing utility or deleting a literal copy.

## Scope

Default target:

```bash
git status --short
git diff --stat HEAD
git diff --stat @{upstream}...HEAD   # if branched (no upstream: main...HEAD, then HEAD~1)
```

- **Uncommitted changes present** → target those files.
- **Clean working tree** → target the latest commit (`git show HEAD --name-only`).
- **Caller passes explicit paths** → scope to those.

**Cover every changed file.** Do not drop files by topic or subsystem ("that's backend dev-infra, this is the frontend feature"). Every changed file goes through all three lenses — a duplication spanning a backend helper and a frontend util still counts, and a 3-way repeat in a file you mentally set aside is exactly what gets missed. If a changed file truly isn't worth polishing it must fall under a Skip category below; name it in the report rather than silently excluding it.

Skip entirely on: pure rename/move commits, dependency bumps, generated code (lockfiles, OpenAPI clients, compiled assets), prototype/throwaway code the user is still exploring.

## Pass 1 — Deslop (three-lens fan-out + resolution)

The signature pattern from the original built-in `/simplify`: each lens reads the **full** diff but applies a different heuristic, then a resolution step merges the proposals.

### Fan-out (always)

Always spawn three sub-agents in parallel via `Agent` with `subagent_type: general-purpose`, regardless of diff size. Hand each the same diff plus only its lens prompt. Each returns a structured proposal list — `{file, line_range, before, after, rationale}` — and does **not** edit files itself.

```
Agent A — AI cruft & dead code lens
Agent B — code reuse & duplication lens
Agent C — clarity & efficiency lens
```

### Lens A — AI cruft & dead code

- Comments that restate what the code does, reference the current task, or break local comment style
- Defensive `try/catch` or null checks on trusted internal call paths
- Casts to `any` / `# type: ignore` used to silence type errors instead of fixing them
- Validation, fallbacks, or error handling for scenarios that can't actually happen
- Half-finished implementations, dead code, leftover scaffolding
- Backwards-compatibility shims for code that has no callers yet
- Unused `_` prefixed vars, re-exports added "just in case", `// removed: ...` placeholders

### Lens B — code reuse & duplication

- **Unused imports** and unreferenced top-level declarations
- **Redundant variables** — vars assigned once and used once, parallel vars holding the same value, intermediate names that don't earn their keep
- Three or more near-duplicate blocks where one well-named helper would collapse them. When you find one copy, **grep the whole repo for every sibling and count them all** before proposing — a dup you read as 2-way is often 3-way, and the true count decides where the helper should live.
- Logic already implemented elsewhere in the codebase. **Operationalize, don't just intend**: for each non-trivial inline implementation (param merging, formatting, debounce, date math, port selection, …) grep `src/utils`, `src/hooks`, and sibling directories by *behavior keyword* (`URLSearchParams`, `Params`, `debounce`, …) before concluding "not reusable". "No helper exists" counts only after the grep.
- Repeated literal/constant strings that should be named
- Functions that recompute the same value multiple times in a request lifecycle

### Lens C — clarity & efficiency

- Deep nesting where early returns or guard clauses would flatten the flow
- **Overly complex conditionals** — long boolean chains, redundant guards, conditions that always evaluate the same
- Names that no longer match what the code does
- Unnecessary work in hot paths (recomputing in loops, O(n²) where O(n) is trivial, sync I/O in async paths, eager evaluation of unused branches)
- `await` inside loops where `Promise.all` is correct
- Cheap-but-impactful perf wins: memoization candidates, redundant DOM reads, repeated `JSON.parse` of the same payload
- Long-lived objects built from closures or captured environments — they keep the whole enclosing scope alive for the object's lifetime (a memory leak when that scope holds large values); prefer a class/struct that copies only the fields it needs

### Resolution step (main agent)

After lenses return:

1. **Dedupe** — collapse proposals that touch the same `file:line_range`; prefer the proposal with the most specific rationale.
2. **Filter** — drop any proposal that:
   - Changes observable behavior (e.g., removes a check the user could see)
   - Conflicts with another lens's proposal that the main agent judges more important
   - Looks like a false positive on closer read (helper actually has callers, "unused" import is a type-only re-export, etc.)
   - **Fights the local house style** — before collapsing repeated blocks into an abstraction, open the sibling files in the same directory. If the immediate neighbors enumerate explicitly (especially when this file already imports and renders one of them), prefer consistency: reject the abstraction or downgrade it to an opt-in note. This filter is for **net-new abstractions only** — never use it to drop a reuse-of-existing-helper or literal-dedup finding (see Posture).

   When you reject, **state the narrowest version of the proposal and refute that exact transform**, not a broader one the lens never made. ("Can't merge the two `<List>`s" is not grounds to drop "extract the shared row shell".) Strawman rejections quietly bury real wins.
3. **Apply** — main agent edits files directly, no `AskUserQuestion`, **for edits confined to the diff**. *Exception — out-of-diff edits*: when a fix (usually a de-duplication) requires a file outside the current diff, do **not** auto-apply — the blast radius and drift risk are a different class. Auto-edit the in-diff copy only if that alone is safe and coherent; otherwise surface the whole change as a proposal with the sibling list and rationale and let the user confirm.
4. **Record** — keep a tally of `proposed / deduped / filtered / applied` per lens for the final report.
5. **Recall gate** — before declaring the pass done, fill in the search surfaces and confirm each was actually checked, not assumed: utils/hooks grepped by keyword? every changed file seen by every lens? every copy of each found duplicate counted? A "clean diff" verdict earns trust only *after* this list is complete — "found nothing" must mean "searched and found nothing", never "didn't look". Any unchecked surface → check it before reporting.

## Pass 2 — Structural (ambitious)

Runs after Pass 1 lands. Single-agent — Pass 2 needs whole-diff context and shouldn't race against itself. Look for "code judo": restructurings that preserve behavior but make the implementation feel inevitable in hindsight.

> Rethink how to structure these changes to meaningfully improve code quality without impacting behavior. Improve abstractions, modularity, reduce spaghetti, improve succinctness and legibility. Be ambitious — if there's a clear path to improving the implementation that involves restructuring some of the codebase, propose it.

**Targets:**

- Helpers, conditionals, or layers that can disappear because the surrounding code already handles the case
- Premature abstractions: parameters that always have one value, wrappers with one caller, interfaces with one impl
- Conditional growth that signals a missing data structure (state machine, lookup table, polymorphism)
- Files growing past ~500 lines that should split by responsibility
- Coupling between modules that should be unidirectional
- Changes made at the wrong altitude — special cases layered on shared infrastructure instead of a fix in the underlying mechanism; prefer generalizing one level down over stacking band-aids
- Names that no longer match what the code does

**Guardrails:**

- Behavior unchanged. If a restructuring is correct only because of an invariant the codebase doesn't enforce, leave it.
- Before inlining a single-caller helper, ask whether the helper carries documentation, testability, or future-extension value worth preserving — when in doubt, leave it.
- **Confirm before large changes** — anything that moves files, renames public APIs, or rewrites more than ~50 lines uses `AskUserQuestion` with a one-line rationale and the diff outline before touching code.
- Small contained simplifications (delete unused helper, inline single-caller function, collapse nested `if`, hoist a constant) apply directly.
- Don't invent abstractions for hypothetical future requirements. Three similar lines is better than a premature abstraction.
- **Match the local pattern.** The "missing data structure" target above (lookup table, config array, polymorphism) is exactly what re-proposes a divergent abstraction. If sibling files in the same directory solve the same shape explicitly, a shorter-but-divergent restructuring is a consistency regression — leave it, or mark it opt-in. (Reuse of an *existing* shared helper is not divergence — that still applies.)

## Verification

After Pass 1 and again after Pass 2, run the lightest available correctness check on the touched files:

- TypeScript projects: `tsc --noEmit` on the touched files (or the whole project if config requires it)
- Python: `mypy` / `ruff check` if configured
- If a focused test suite exists for the touched files, run it
- If nothing applies, skip — don't invent a check

If verification fails, **revert the offending edit by reversing it with `Edit`** — apply the exact `after → before` of the proposal you landed — and report it in the output. Never revert with `git checkout --` / `git restore`: polish usually edits on top of the user's uncommitted changes, and those commands wipe the user's work together with yours. Never push through a verification failure.

## Output

One compact report after both passes:

```
Pass 1 (3-lens deslop)
  Lens A — proposed N, deduped X, filtered Y, applied Z
  Lens B — proposed N, deduped X, filtered Y, applied Z
  Lens C — proposed N, deduped X, filtered Y, applied Z

Pass 2 (structural)
  Applied: <bullet list of small landings>
  Proposed (awaiting confirm): <bullet list; mark ⚠ out-of-diff when it touches files beyond the diff>

Rejected (reason): <considered and deliberately left — one line each with the why>
Excluded from scope: <changed files not polished + the Skip category that justifies it | none>

Verification: <command> → pass | fail (reverted: <file>)
```

Keep it tight — one line per entry. The diff is the proof.

## When NOT to run

- Caller is mid-debug and the diff is intentionally instrumented (extra logs, throws, asserts)
- User explicitly says "ship as-is" or "prototype"
- Diff is a revert
- Polishing would unblock zero readers — e.g., a one-line config tweak

## Invocation

Model-invocable. Trigger automatically when:

- The user finishes a non-trivial change (don't wait for an explicit "clean this up")
- The user asks to "polish", "clean up", "deslop", "simplify"
- A skill like `/gbase:go` or `/gbase:monitor` chains it before opening a PR or after an auto-fix
- The user explicitly invokes `/gbase:polish`

Skip auto-invocation on tiny diffs (<10 lines) and on diffs that are pure formatter output.
