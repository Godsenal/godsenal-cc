---
name: monitor
description: "Watches a PR until it merges or closes: fixes clear CI failures and requested review changes, resolves safe conflicts, replies on what it handles, asks about the rest; --merge merges once green, --until-settled stops when CI and review bots conclude. Use to babysit a PR to merge; also gbase:go's tail."
allowed-tools: Bash Read Edit Write Glob Grep AskUserQuestion Skill Agent Monitor
---

# /gbase:monitor

Keep the current branch's PR moving until merge or close. Auto-triggering starts the watch; it never licenses a unilateral merge, force-push, or ambiguous edit.

## 출력 언어

사용자에게 보이는 글은 **한국어**로 쓰고, 코드·명령·상태 라벨·커밋·브랜치는 레포 관례를 따른다. 세부: [output-language.md](../../references/output-language.md).

## Safety

- No `git reset --hard`, `git checkout .`, `git clean -f`, plain `git push --force`, or `git stash drop` (unless the user asks).
- `git push --force-with-lease` and `git checkout --ours/--theirs` only while resolving a conflict by [conflicts.md](references/conflicts.md); if the lease is rejected, stop.
- One commit per autonomous fix. Stop and surface on any push or merge error instead of retrying destructively.
- Never resolve threads, re-request review, dismiss approvals, or reply twice to the same comment.
- `gh pr ready` and `gh pr merge` only by [merge.md](references/merge.md).

## Loop

The PR's state comes from one script (`scripts/pr-status` in this skill's directory), not from `gh` calls of your own. Its `next:` lines say what to handle, in order:

```bash
"${CLAUDE_SKILL_DIR}/scripts/pr-status" --start    # the first sweep; add --merge when invoked with it, --hold-replies / --post-replies when asked not to / to reply
```

1. Run it. Pre-existing comments are in that first output: handle every `next:` line before waiting.
2. `--until-settled` (always the case under `AGENT_SHIP_OWNER=orchestrator`) → the run ends at a verdict, not at merge: read [settle.md](references/settle.md) now and follow it instead of step 3.
3. Otherwise start a persistent `Monitor` on `"${CLAUDE_SKILL_DIR}/scripts/pr-status" watch`: it exits at merge or close.
4. Unless `--no-review`, run the self-review once, now (below).
5. On each change, run the script again (no `--start`) and handle its `next:` lines top to bottom.

Per `next:` line:

| `next:` | Do |
|---|---|
| `conflict` | Read [conflicts.md](references/conflicts.md). |
| `comments` | Read [comments.md](references/comments.md) before touching any of them. |
| `ci` | Fix what the diff caused, from the log on the `failed:` line, and push. A failure it didn't cause is reported, not fixed. Still failing after two fixes → [premise.md](../../references/premise.md). |
| `wait` | Nothing to do yet. |
| `settled` | With `--draft` or `--merge`, read [merge.md](references/merge.md); otherwise keep watching for reviews. |

Any other `next:` line (`notes`, `unstarted`, `done`, and under `--until-settled` `give up` and `limit`) says what to do itself.

A `replies: draft` line → read [held-replies.md](references/held-replies.md) before any comment: nothing is posted.

A `link:` line is a build or preview someone can try: pass each one on once, with its source and commit. Don't open it or post it back.

Under `AGENT_HEADLESS=1` (check `printenv AGENT_HEADLESS` before asking) nothing is asked: follow [headless.md](../../references/headless.md). A merge whose gate would ask isn't made.

## Self-review

Launch an `Agent` (`general-purpose`, `run_in_background: false`: nothing merges or is committed until it returns) told to run `Skill(skill: "gbase:review", args: "post-PR mode; defer, don't ask; <PR diff scope>")` and return its table and tally line (no `Agent` tool → call the skill directly). `gbase:go` passes `--no-review` when it reviewed before the PR; if you can't tell whether the diff was reviewed, run it. Relay the report, ask about anything worth fixing before merge, and polish an approved fix per comments.md.

## Errors

An `error:` line from the script: relay it and stop. Push rejected as out of date → `git pull --rebase`, retry once; conflicts go through conflicts.md.
