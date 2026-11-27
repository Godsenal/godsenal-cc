# `go` under an orchestrator

Read when Step 1's `printenv | grep '^AGENT_'` prints anything. The variables are defined in [orchestrator.md](../../../references/orchestrator.md). Under `AGENT_HEADLESS=1` nothing is asked: follow [headless.md](../../../references/headless.md), with the defaults below.

## 1. Scope

Under `AGENT_SHIP_OWNER=orchestrator`, or `AGENT_HEADLESS=1` with any owner, a clean tree targets every commit on the branch that isn't in the base (`<base>...HEAD`; base = `origin/<default>` when it exists, else the local default branch): the orchestrator's agent may have committed as it worked.

A headless run reviews `low` before the PR, because it often ends before any monitor self-review and under `AGENT_SHIP_OWNER=orchestrator` there is no Step 6. `stage-delta mark low` then owes `code-review low`, by [review.md](review.md), and its Step 3 args get `; one skeptic for low/medium` like `medium`.

## 2–3. Review ∥ polish

The agents inherit the `AGENT_*` variables, so polish and review apply their own headless defaults. If the finder hasn't returned when polish finishes, wait on its completion notice, not on a wakeup. Review's table is not the run's report: a headless `work` run stopped there once, with the change uncommitted and no PR.

## 4. Verification gate

Under `AGENT_HEADLESS=1`, a diff-caused failure that survives two fix attempts: open the PR anyway with the failure in Evidence, as a draft when the agent owns the PR (Step 5's args then start with `--draft `).

With `AGENT_EVIDENCE_FILE` set, read the [Evidence file](../../../references/orchestrator.md#evidence-file) section before writing the first line: the caller parses its fixed fields, written with the JSON one-liner there. Append lines as results become final: one per check command and per behavior feature (with `input` when it ran on a chosen input), plus one each for review (after Step 3) and polish. A skipped step still gets its `skip` line.

## 5. Branch & PR

Under `AGENT_SHIP_OWNER=orchestrator` the `branch-pr` args start with `Ship-owner: orchestrator; PR-body-file: <$AGENT_PR_BODY_FILE, else $(git rev-parse --absolute-git-dir)/gbase/pr-body.md>; `, and `branch-pr` commits locally and writes the draft instead of pushing. Then stop: no Step 6. The report ends with branch-pr's `ship:` and `PR 본문 초안:` lines and the deferred-findings table.

When the agent owns shipping, the report must carry the `pr: <url>` line at column 0; the caller greps it.

## 6. Monitor

Under `AGENT_HEADLESS=1` (the owner is the agent here): add `--until-settled` to the args (the `--no-review` rule still applies) instead of the persistent watch, which has no one to end it under `claude -p`; monitor pushes its fixes, replies, and ends with one `settle:` line.

Pass `--merge` along with it only when this invocation or the task itself asked for the merge in words ("머지", "merge", `--merge`); a project instruction alone is not enough here. Monitor then merges once the head settles, under its `--merge` gates, and a gate that would ask leaves a `결정 필요:` line instead. Never run `gh pr merge` yourself: a hand merge skips the settle wait and leaves no `settle:` line (14 PRs merged that way in one week, with their checks red). A `--draft` PR stays a draft; say so in a `결정 필요:` line.

In the same headless run, deferred findings shrink to their table: nothing is asked or pushed after monitor, so the `settle:` verdict stays true for the head it names.
