---
name: polish
description: "Two-pass code polish on the current diff — first strip AI-generated slop (unnecessary comments, defensive try/catch, `as any`, deep nesting, dead fallbacks), then hunt for ambitious structural simplifications that preserve behavior. Use after writing code, before review, or when a diff feels bloated. Replaces `/simplify` and the bundled `/code-review` for the polish role in `gbase:go` and `gbase:monitor`."
allowed-tools: Bash Read Edit Write Glob Grep AskUserQuestion
---

# /gbase:polish

Two polish passes on the current diff (or files the caller hands in). Both passes are **behavior-preserving** — no bug fixes, no contract changes, no API tweaks. If a real correctness bug surfaces during polishing, stop and surface it to the user rather than silently patching it.

## Scope

Default target:

```bash
git status --short
git diff --stat HEAD
git diff --stat origin/main...HEAD   # if branched
```

- **Uncommitted changes present** → target those files.
- **Clean working tree** → target the latest commit (`git show HEAD --name-only`).
- **Caller passes explicit paths** → scope to those.

Skip entirely on: pure rename/move commits, dependency bumps, generated code (lockfiles, OpenAPI clients, compiled assets), prototype/throwaway code the user is still exploring.

## Pass 1 — Deslop (mechanical)

Always runs first. Remove AI-generated cruft, line by line.

**Targets:**

- Comments that restate what the code does, reference the current task, or break local comment style
- Defensive `try/catch` or null checks on trusted internal call paths
- Casts to `any` / `# type: ignore` used to silence type errors instead of fixing them
- Deep nesting where early returns or guard clauses would flatten the flow
- Validation, fallbacks, or error handling for scenarios that can't actually happen
- Half-finished implementations, dead code, leftover scaffolding
- Backwards-compatibility shims for code that has no callers yet
- Unused `_` prefixed vars, re-exports added "just in case", `// removed: ...` placeholders

**Guardrails:**

- Behavior unchanged. If removing a check changes observable behavior, leave it.
- Minimal, focused edits. No drive-by renames, no formatting churn.
- Apply directly — no confirmation needed for these.

## Pass 2 — Structural (ambitious)

Runs after Pass 1 lands. Look for "code judo": restructurings that preserve behavior but make the implementation feel inevitable in hindsight.

> Rethink how to structure these changes to meaningfully improve code quality without impacting behavior. Improve abstractions, modularity, reduce spaghetti, improve succinctness and legibility. Be ambitious — if there's a clear path to improving the implementation that involves restructuring some of the codebase, propose it.

**Targets:**

- Helpers, conditionals, or layers that can disappear because the surrounding code already handles the case
- Premature abstractions: parameters that always have one value, wrappers with one caller, interfaces with one impl
- Conditional growth that signals a missing data structure (state machine, lookup table, polymorphism)
- Files growing past ~500 lines that should split by responsibility
- Coupling between modules that should be unidirectional
- Three or more near-duplicate blocks that one well-named helper would collapse
- Names that no longer match what the code does

**Guardrails:**

- Behavior unchanged. If a restructuring is correct only because of an invariant the codebase doesn't enforce, leave it.
- **Confirm before large changes** — anything that moves files, renames public APIs, or rewrites more than ~50 lines uses `AskUserQuestion` with a one-line rationale and the diff outline before touching code.
- Small contained simplifications (delete unused helper, inline single-caller function, collapse nested `if`, hoist a constant) apply directly.
- Don't invent abstractions for hypothetical future requirements. Three similar lines is better than a premature abstraction.

## Output

After both passes, return one compact report:

1. **Deslop edits** — bullet list (`file:line` when useful)
2. **Structural edits applied** — bullets for the small ones that landed
3. **Structural proposals** — if any large restructurings need sign-off, list them with a one-line rationale each

Keep the summary under ~10 lines. The diff is the proof.

## When NOT to run

- Caller is mid-debug and the diff is intentionally instrumented (extra logs, throws, asserts)
- User explicitly says "ship as-is" or "prototype"
- Diff is a revert
- Polishing would unblock zero readers — e.g., a one-line config tweak

## Invocation

Model-invocable. Trigger automatically when:

- The user finishes a non-trivial change and asks to "polish", "clean up", "deslop", "simplify"
- A skill like `/gbase:go` or `/gbase:monitor` chains it before opening a PR or after an auto-fix
- The user explicitly invokes `/gbase:polish`

Skip auto-invocation on tiny diffs (<10 lines) and on diffs that are pure formatter output.
