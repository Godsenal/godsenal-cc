# `--draft`, `--merge`, `--preview`, reply flags, and deferred findings

Read before Step 5 when `go` was invoked with `--draft`, `--merge`, `--preview`, `--hold-replies`, or `--post-replies`, or review deferred a finding.

## Deferred findings

After monitor starts, surface them: a severity-ordered table (`file:line`, failure scenario, what the fix takes), with `AskUserQuestion` on any worth resolving before merge. Monitor never received them, so `go` applies, commits, and pushes any fix the user accepts, then drops that item, and its count, from the PR body's `## Review focus` or its folded list, switching to the `[!NOTE]` box when none remain (`gh pr edit --body`, after the same `gbase:unslop` pass as the first body).

An `open` row from polish's `Comments:` line (a constraint comment deleted with no check in its place, a workaround left for a later change) is in `Deferred:` only so the PR body carries it. It is not a finding to settle: leave it out of the count passed to monitor, and it holds neither the ready flip nor `--merge`.

## `--draft`

Pass `--draft` to `branch-pr` at the front of its args (`"--draft Risk: …; Verification: …; Deferred: …"`) and to monitor, with the count of unresolved deferred findings: monitor holds the ready flip until CI is green and that count is zero.

## `--preview`

The user wants to read the change before its PR exists, this once (also "PR 올리기 전에 보여 줘"). Put `--preview` at the front of `branch-pr`'s args, ahead of `--draft`: it stops before the push and asks ([preview.md](../../branch-pr/references/preview.md)). A `--merge` given with it waits for the PR the user opens from that question.

## `--hold-replies`, `--post-replies`

The user doesn't want replies posted on the PR under their name this once ("답글은 달지 마"), or wants them posted although their environment file says `review replies: draft` ("답글 달아"). Add the flag to monitor's args in Step 6; monitor passes it to `pr-status`, and [held-replies.md](../../monitor/references/held-replies.md) is monitor's to read. Without a flag the environment file decides, and `go` reads nothing for it. A fix `go` itself pushes for a deferred finding answers no reviewer, so it is pushed either way.

## `--merge`

Settle the deferred findings first: fix or decline each. Pass `--merge` to monitor only once none remain open, plus `verified-locally` when Step 4 passed in this run. Otherwise drop `--merge` and say why the PR stays open. Never run `gh pr merge` yourself: monitor's gate waits for the head to settle, and a hand merge skips it.
