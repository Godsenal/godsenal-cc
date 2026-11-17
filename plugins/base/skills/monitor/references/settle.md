# `--until-settled`

Read when monitor was invoked with `--until-settled` (the only mode run under `AGENT_SHIP_OWNER=orchestrator`). Same sweep, fixes, self-review, and replies as the loop, but the run ends once the head settles, not at merge.

## Wait

```bash
<the loop's pr-status script> wait     # add --merge when invoked with it, --verified-locally when go passed it
```

- Call it in the foreground, again and again; no persistent `Monitor`. Each call returns within 5 minutes with a status line per poll, or as soon as something needs action. A caller may kill a run that prints nothing for ~10 minutes.
- Handle its `next:` lines as in the loop. **Each fix you push is a new head**; the script starts that head's wait over.
- The script decides what "settled" means (every check concluded, every expected automated reviewer finished on this head), gives up 30 minutes into one head, and prints `next: limit` after the third fix you pushed in this watch. On `limit`, push no more fixes: a run that keeps fixing is usually chasing a problem the approach has.

## Verdict

End with exactly one line, the script's `settle:` line ([meaning](../../../references/orchestrator.md#settle)):

- `settle: 수렴 @<sha>`, or `settle: 미확정 @<sha> — 안 옴: …` after `give up` or `limit` — as printed.
- `settle: 사람 필요 @<sha> — …` — the script prints it whenever a failed check, an open comment, or a conflict exists. It becomes the verdict only for what you could not fix or answer here; fix what you can, push, and wait on the new head first.

## What it never does

- **Merges only with `--merge`**, and only after `수렴`, or when nothing is open except checks that never started for account reasons and `go` passed `verified-locally`. Then follow [merge.md](merge.md) and end with `settle: 수렴 @<short-sha> — merged <merge short-sha>`. Any other verdict, or a gate that would ask (a merge that deploys), doesn't merge: the `settle:` line stands and a `결정 필요:` line says what a person does.
- **Never rebases or force-pushes**: a conflict is reported (`사람 필요`), not resolved. The one exception is a rebase, and only when the invocation explicitly asks to rebase (`--until-settled rebase onto main`): rebase onto the base once, resolve by [conflicts.md](conflicts.md), and push with `--force-with-lease`. A finding, a recommendation, or an `AGENT_ASK_CMD` answer is never that instruction.

## `AGENT_SHIP_OWNER=orchestrator`

Check `printenv AGENT_SHIP_OWNER`. Another program owns the remote, so nothing leaves the machine:

- Fixes are committed locally, one per fix, and **never pushed**. Nothing is posted either: no reply, comment, or `gh pr ready`. The replies you would have posted go in the report. A requested rebase stays local too: `ship: local <branch> @<short-sha> — rebased onto <base>, not pushed (needs --force-with-lease)`.
- The wait covers the pushed head only and doesn't start over. Once you have fixed something locally, call `wait --handled`: the failure still shows on the pushed head, and without the flag every call would return at once. A failure or comment fixed by a local commit counts as handled, but with local commits the verdict is never `수렴`: it is `settle: 미확정 @<pushed sha> — 푸시 대기: <n> commits`, unless `사람 필요` applies.
- With local commits, write an updated PR draft to `AGENT_PR_BODY_FILE` (default `$(git rev-parse --absolute-git-dir)/gbase/pr-body.md`) in the [draft format](../../../references/orchestrator.md#ship-owner-orchestrator): the title and body from `gh pr view --json title,body`, with `## Evidence` (and `## Change outline` if the shape changed) updated for the new commits. Before the `settle:` line, report `ship: local <branch> @<short-sha> — <n> commits, not pushed` and `PR 본문 초안: <path>`.

## Evidence

With `AGENT_EVIDENCE_FILE` set, append [evidence lines](../../../references/orchestrator.md#evidence-file): one `checks` line per command you ran to verify a fix, a `review` line when the self-review ran (or `open` for an unreviewed conflict resolution), and one `settle` line.
