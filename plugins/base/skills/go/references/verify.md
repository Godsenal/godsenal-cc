# Verification gate: the rest of Step 4

Read when the change is `medium` or `high`, a check fails, or the repo has no verify block.

## Which checks

The `<!-- gbase:verify:start -->` block is written by `gbase:setup`; every line was run once except those marked `unverified locally`. Without a block, discover the checks (`CLAUDE.md`/`AGENTS.md`, `package.json` scripts, Makefile, CI workflows) and mention `/gbase:setup` once in the report. If the repo defines none, skip and say so; don't invent or install tools.

Keep the gate to fast checks: lint, typecheck, unit tests. Native builds (`pod install`, `xcodebuild`, Gradle assemble), simulator or emulator runs, and E2E suites belong to CI. Two exceptions: a `typecheck (no CI)` line in the block (setup writes it only when no CI job builds the app, so it is the repo's only compile gate), and the repo's own verify skill below. The full suite is CI's when a scoped run covers the diff.

## A check fails

Bias toward shipping:

- Diff-caused and mechanical (type error, lint, missing import) → fix and re-run, at most twice: the failing file or case first, then the scoped command once.
- Pre-existing (files the diff didn't touch), flaky, or environment-dependent (no DB, no device, missing env) → note and proceed.
- Diff-caused and still failing after two attempts → `AskUserQuestion` with the output: fix now / open the PR anyway / abort.

## Behavior check

Required on `medium` and `high` when the diff changes what a user or caller observes. It runs once per change, not once per skill.

- **Reuse the route's run.** Take the passing `behavior:` lines `gbase:work` wrote for this task as they are, except for a feature whose files a review fix touched after that run: re-run that one. A route `skip` line is not reused; try the feature here.
- **Otherwise run it here.** The repo's verify skill, `.claude/skills/verify-*/` (from `gbase:create-verify`) or `.claude/skills/verify/` (pstack's generator), at the root or in the touched package, for the features in its `features/` map that the diff touches. Without one, a CLI or script run that exercises the change and needs no build, device, or server start; don't build a harness for it.
- **Required means evidence or a reason.** An unreachable precondition (no simulator, no test account, no such run) is `behavior: skip — <reason>`, noted and passed. A diff-caused failure goes through the fix-twice-then-ask rule above.
- **Say what it ran on.** When a check ran on a chosen input (a fixture, sample files, a simulator) and the bug report or real use has a different kind (resolution, format, metadata, device), name both: 1024px messenger copies passed while the phone's full-size originals still failed, and the report never said the inputs differed.

Report `behavior: <feature> → pass (<evidence dir>)` per feature, adding `(input: <what it ran on>; differs: <difference>)` when the last point applies. These lines and the `verify:` lines go to `branch-pr` as the PR's `## Evidence`; an `input` with `differs:` becomes a Review focus item there.
