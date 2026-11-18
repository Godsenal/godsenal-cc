# `--draft`, `--merge`, and deferred findings

Read before Step 5 when `go` was invoked with `--draft` or `--merge`, or review deferred a finding.

## Deferred findings

After monitor starts, surface them: a severity-ordered table (`file:line`, failure scenario, what the fix takes), with `AskUserQuestion` on any worth resolving before merge. Monitor never received them, so `go` applies, commits, and pushes any fix the user accepts, then drops that item, and its count, from the PR body's `## Review focus` or its folded list, switching to the `[!NOTE]` box when none remain (`gh pr edit --body`, after the same `gbase:unslop` pass as the first body).

An `open` row from polish's `Comments:` line (a constraint comment deleted with no check in its place, a workaround left for a later change) is in `Deferred:` only so the PR body carries it. It is not a finding to settle: leave it out of the count passed to monitor, and it holds neither the ready flip nor `--merge`.

## `--draft`

Pass `--draft` to `branch-pr` at the front of its args (`"--draft Risk: …; Verification: …; Deferred: …"`) and to monitor, with the count of unresolved deferred findings: monitor holds the ready flip until CI is green and that count is zero.

## `--merge`

Settle the deferred findings first: fix or decline each. Pass `--merge` to monitor only once none remain open, plus `verified-locally` when Step 4 passed in this run. Otherwise drop `--merge` and say why the PR stays open. Never run `gh pr merge` yourself: monitor's gate waits for the head to settle, and a hand merge skips it.
