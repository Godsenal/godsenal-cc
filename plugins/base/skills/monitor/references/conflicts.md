# Conflicts

Read when `pr-status` prints `next: conflict`. Under `--until-settled` a conflict is reported, not resolved, unless the invocation explicitly asked to rebase ([settle.md](settle.md)).

**Resolve automatically:**

- Lockfiles (`package-lock.json`, `pnpm-lock.yaml`, `yarn.lock`, `bun.lock`, `Gemfile.lock`, `poetry.lock`, `Cargo.lock`, `go.sum`, …): take base, regenerate with the matching package manager. `Podfile.lock` only if `pod install` works locally; otherwise ask.
- Generated artifacts (`dist/`, `build/`, `*.min.js`, `*.map`): take base, regenerate if a build script exists.
- Pure additions at the same spot (separate imports, enum entries, test cases) that don't reference the same identifier: keep both.
- Whitespace-only: rerun the formatter.

**Ask** for everything else: same-line semantic edits, migrations/schemas, config files (`.env*`, `tsconfig.json`, `app.json`/`app.config.*`, `eas.json`, `Info.plist`, `build.gradle*`, `Podfile`, `next.config.*`, CI yamls), conflicts over ~30 lines, rebases replaying more than ~5 commits, renames modified on the other side.

After resolving: polish the resolved files when the resolution rewrote logic (an `Agent`, `run_in_background: false`, told to run `Skill(skill: "gbase:polish", args: "<resolved files>")` and return its report, leaving what polish would ask about unapplied under `awaiting confirm` (a subagent can't ask)) and `git add` them, then `git rebase --continue`, `git push --force-with-lease`. A conflict that reappears after a clean rebase means a parallel PR is fighting the same lines: stop and surface.

**On a `high` PR, ask whether the earlier verification still describes the branch** (the PR body's risk line says `high`: `gh pr view --json body`). After any rebase or base merge, conflicted or not, and before the push:

```bash
<the loop's pr-status script> patch --base origin/<base>     # `git patch-id` of the pushed head's change against HEAD's
```

Its `next:` line decides. `nothing to re-verify` (the same patch on a new base, or only wording changed) → push; CI covers the new head. `one verifier` → one `Agent` (`run_in_background: false`) that didn't resolve the conflict reruns the verify block's checks and the behavior check for the files the line names, without editing; its `verify:` and `behavior:` lines go in the report and the evidence file, and a failure is fixed like a `ci` failure before the push. The full verification ran once, before the PR: this is never a second review. Lower tiers skip the step, and CI on the new head is their re-check.

**A resolution that combined both sides' content** (anything past the auto-resolve list, such as merging two PRs' rules into one file) gets a review before the push, from an `Agent` (`run_in_background: false`) told to run `Skill(skill: "gbase:review", args: "report only; <resolved files>, diffed against the new base")` and return its table; its findings go through the same classification as a review comment ([comments.md](comments.md)). When it can't run, push only with a `review` `open` [evidence line](../../../references/orchestrator.md#evidence-file) whose `detail` is `conflict resolution unreviewed: <files>`, and say so in the report. One such merge of two same-day rule PRs moved rules and reworded one, and went to main with no review.
