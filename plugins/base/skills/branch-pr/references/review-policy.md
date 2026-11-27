# Review policy

Read when `ship-prep start` prints a `review policy:` line. That line means the environment file ([environment.md](../../../references/environment.md)) asks something of every PR opened here. A run without the line reads nothing more, and nothing below applies to it.

The four lines, as the user writes them:

```markdown
## Conventions
- Reviewers: @alice, acme/backend
- Labels: needs-review
- Commit sign-off: on

## Shipping
- PR size: 400 lines
```

## Reviewers and labels

`ship-prep open` passes them to `gh pr create` as `--reviewer` and `--label`; there is no step for you. It prints `requested: …` when GitHub took them. When GitHub refuses one (a login that left, the PR's own author, a label nobody made yet), it keeps or opens the PR without what was refused and prints a `note:`. Put that note in the report. Never retry another way. A draft PR gets its reviewers too. GitHub shows them it is a draft, and asking only later would need a step that nothing runs.

A `Reviewers:` line that isn't a list of logins and `org/team`s (prose like "CODEOWNERS가 배정한다") requests nobody, and `start` says so in a `note:`. CODEOWNERS works as before, on GitHub's side.

**Under `Ship-owner: orchestrator`** ([local-mode.md](local-mode.md)), nothing is opened here. `start --local` prints `reviewers: <a, b>` and `labels: <a, b>` lines. Copy them into the report as they are, next to `ship:`. The caller that opens the PR asks for them.

## Commit sign-off

With `Commit sign-off: on`, make every commit with `git commit -s`, so it carries the DCO `Signed-off-by:` trailer. `ship-prep check`, `preview`, and `open` refuse a commit that no remote has and that lacks the author's own trailer, and nothing is pushed. A merge commit needs none. Fix it with the `git rebase --signoff <sha>^` the error names, which rewrites only those unpushed commits. With a merge among them the error names no rebase, since one would write the merged-in commits again: redo the branch's own commits without the merge, or ask. A commit that is already on a remote is never rewritten for this: say so in the report. Monitor's fix commits follow the same rule, from the `sign-off:` line `pr-status` prints.

## Signing

When `commit.gpgsign` is on, `start` prints a `signing:` line. A commit that fails to sign (a locked key, no agent) stops the run. **Never `--no-gpg-sign`, `-c commit.gpgsign=false`, or any other way past it.** The team's branch protection may require signed commits, and an unsigned commit only fails later, on GitHub. Report the git error and stop. Headless, write one `결정 필요:` line: `커밋 서명 실패 → 커밋하지 않음`. `check`, `preview`, and `open` refuse an unsigned unpushed commit too, so a commit made some other way doesn't reach the PR.

## PR size

`PR size: <N> lines` (or `<N>줄`) counts the lines added plus removed since the branch left the base. A `PR size:` line with no number it can read gets a `note:` from `start` and checks nothing. A change over it still opens, since a PR can be closed and split later. `start` prints `size: <n> lines, over the <N> …`. The draft's Review focus then opens with item 1, which proposes how to split it (which part goes first, and why it can go alone) and ends with `(크기)`:

```markdown
> [!IMPORTANT]
> **사람이 볼 곳 2건**
> 1. **두 PR로 나눌 수 있다** 스키마 변경을 먼저, 화면을 그다음에 (크기)
>    612줄 중 스키마 180줄은 혼자 배포된다
```

`ship-prep check` and `open` refuse a draft over the size whose item 1 lacks the `(크기)` mark. With `PR size: <N> lines, ask`, `start` also prints an `ask:` line, and that question is settled before the commit like any other `ask:` line. Headless, follow [headless.md](../../../references/headless.md). Its recommendation here is to open the change as one PR with item 1, plus a `결정 필요:` line. An answer of "open it as one" still keeps item 1, which then says the person chose one PR.
