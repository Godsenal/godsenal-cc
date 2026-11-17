# `high` risk: what it adds to Steps 4 and 6

Read when Step 1 classified the change `high`, after [verify.md](verify.md).
## 4. An agent that didn't write the code checks the behavior

On `high` the `behavior:` lines `gbase:work` wrote are the list of features to check, not results: the session that wrote a change checks what it expects to see. Launch one `Agent` for the whole change, not one per feature:

```
Agent(subagent_type: "general-purpose", run_in_background: false, description: "behavior check",
      prompt: "In <repo path>, check on the real surface that this change behaves as intended. Edit no file. Scope: <scope from Step 1>. Features and what a user or caller should observe: <feature — intended behavior, per feature>. Use the repo's verify skill (.claude/skills/verify-*/ or .claude/skills/verify/) for the features in its map, else a CLI or script run that needs no build, device, or server start. You did not write this change: take no claim about it on trust, run it. Return one line per feature: `behavior: <feature> → pass (<command> → <the output that shows it>)`, `behavior: <feature> → fail (<command> → <output>)`, or `behavior: skip — <feature>: <what you could not reach>`. Add `(input: <what it ran on>; differs: <difference>)` when it ran on another kind of input than real use has.")
```

- Without `gbase:work` lines, take the features from the diff: each thing a user or caller observes differently.
- Give it the features and the intended behavior, never the route's results or evidence directories: it would read them instead of running.
- Its lines replace the route's as the `Verification:` lines and the evidence file's `behavior` lines. A `fail` goes through verify.md's fix-twice rule, and a fresh agent checks the fixed feature again; this session's own rerun doesn't close it.
- A `skip` stays a skip: unverified, by verify.md.
- No `Agent` tool here (`go` is itself running in a subagent) → run the check in this session and end each line's evidence with `same session`.

## 4. Order of events: locks, retries, state machines

When the diff changes code whose result depends on the order things happen in (a lock or a queue, a retry or backoff loop, an idempotency key, the transitions of a status field, a scheduler), one run of the surface shows one ordering. Add this to the same agent's prompt, without a second agent:

- **The repo has a formal verification skill** that covers the touched code (a project-local skill written by [create-formal-verification-skill](../../create-formal-verification-skill/SKILL.md); its description names the area) → the agent runs it, and the result is one more `behavior:` line.
- **It has none** → the agent reads [statechart](../../statechart/SKILL.md) (pass the absolute path) and models only the transitions the diff changes, in a scratch folder outside the repo. A path to a state that breaks a rule is `behavior: <feature> → fail` with that path as the evidence. A checker that can't be installed here ([pstack-adapter.md](../../../references/pstack-adapter.md), Installs) is `behavior: skip — <reason>`.
- Writing the project's formal verification skill is not part of a ship run: it picks its own target, installs a checker, and takes a session. When the repo has none and the diff changed such code, say so once in the report as a suggestion (`제안: create-formal-verification-skill — <area>`), never as a `남은 작업:` line, which a caller would start as a run.

A repo that wants this on every change to its queue or worker code lists those paths as always-high in `REVIEW.md`; the tier rule itself doesn't read the diff for concurrency.

## 6. A check that is still open keeps the PR open

A `behavior: skip` or `fail` the agent left is something a person has to look at on a `high` change, so it counts like an unresolved deferred finding in [draft-merge.md](draft-merge.md): drop `--merge`, keep a `--draft` PR a draft, and say which feature and what a person checks (headless: one `결정 필요:` line per feature). `medium` keeps its rule: the `(확인)` item is enough.

Monitor needs no flag for the tier: after a rebase or a base merge it reads the PR body's risk line and, on `high`, asks whether the change that was verified is still the change on the branch ([conflicts.md](../../monitor/references/conflicts.md)).
