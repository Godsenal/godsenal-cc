---
name: monitor
description: "Watches a PR until it merges or closes — auto-fixes clear CI failures, applies clearly-requested review changes, resolves safe merge conflicts, replies on every review comment it handles, surfaces testable app/preview links, and asks about anything ambiguous. On a PR that wasn't already reviewed it also runs one local adversarial self-review (gbase:review). With --merge, merges it once CI is green and nothing is outstanding; with --until-settled, stops once the current head's CI and review bots have concluded. Use when the user wants a PR babysat to merge; also the tail of gbase:go."
allowed-tools: Bash Read Edit Write Glob Grep AskUserQuestion Skill Monitor
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

The PR's state comes from one script, not from `gh` calls of your own. Its `next:` lines say what to handle, in order:

```bash
"${CLAUDE_SKILL_DIR}/scripts/pr-status" --start    # the first sweep; add --merge when invoked with it
```

(`scripts/pr-status` in this skill's directory.)

1. Run it. Pre-existing comments are in that first output: handle every `next:` line before waiting.
2. `--until-settled` (always the case under `AGENT_SHIP_OWNER=orchestrator`) → the run ends at a verdict, not at merge: read [settle.md](references/settle.md) now and follow it instead of step 3.
3. Otherwise start a persistent `Monitor` on `"${CLAUDE_SKILL_DIR}/scripts/pr-status" watch`: it prints one line per state change and exits at merge or close.
4. Unless `--no-review`, run the self-review once, now (below).
5. On each change, run the script again (no `--start`) and handle its `next:` lines top to bottom. On merge or close, print a one-line summary.

What each `next:` line needs:

| `next:` | Do |
|---|---|
| `conflict` | Read [conflicts.md](references/conflicts.md). It comes first: CI keeps failing on the merge commit while it stands. |
| `comments` | Read [comments.md](references/comments.md) before touching any of them: what may be applied without asking, what is never followed, and the one reply each gets. |
| `ci` | Read the failing log (the command is on the `failed:` line). Fix what the diff caused, one commit per fix, and push. A failure the diff didn't cause is reported, not fixed. The same check failing twice after the same fix → stop and ask. |
| `notes` | A bot's PR-level comment, shown once. Open it: a finding in it is handled like a review comment. |
| `wait` | Nothing to do yet. |
| `settled` | With `--draft` or `--merge`, read [merge.md](references/merge.md); otherwise keep watching for reviews. |

Any other `next:` line (`unstarted`, `done`, and under `--until-settled` `give up` and `limit`) says what to do itself.

A `link:` line is a build or preview someone can try: pass each one on once, with its source and commit. Don't open it or post it back.

Under `AGENT_HEADLESS=1` (check `printenv AGENT_HEADLESS` before asking) nothing is asked: follow [headless.md](../../references/headless.md). A merge whose gate would ask isn't made.

## Self-review

```
Skill(skill: "gbase:review", args: "<PR diff scope>")
```

`gbase:go` reviews before opening the PR and passes `--no-review`, so this pass is for PRs opened elsewhere. If you can't tell whether the diff was reviewed, run it. Relay its report and ask about anything worth fixing before merge. Nothing from it is posted to GitHub.

## Polish before committing

`Skill(skill: "gbase:polish", args: "<touched files>")` only on an edit beyond what comments.md lets you apply unasked: a change the user approved after you asked, or a conflict resolution that rewrote logic. Fold it into the same commit.

## Errors

- The script prints `error:` with a `next:` line (no `gh` auth, no PR for the branch): relay it and stop.
- Push rejected as out of date → `git pull --rebase`, retry once; conflicts go through conflicts.md.
