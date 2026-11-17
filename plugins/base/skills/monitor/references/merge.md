# `--draft` and `--merge`

Read when monitor was invoked with `--draft` or `--merge` and the script printed `next: settled` or a `merge:` line.

## `--draft`

Run `gh pr ready` once CI is green and every outstanding finding is resolved: from a self-review this run did, and from the count of deferred findings `gbase:go` passed. Flipping on CI green alone would announce the PR for review with a known defect still in it.

## `--merge`

Only when `--merge` was passed, because the user asked to merge or the project's instructions say to. Never by default.

`pr-status --merge` (add `--verified-locally` when `go` passed it) judges the gate: no failing check (required or not), the head settled, no standing `CHANGES_REQUESTED`, no unanswered review comment, no conflict, a mergeable state. `merge: not now — …` means don't merge. On `merge: gate passed` three things are still yours:

- **No unresolved finding from this run's self-review.** The script can't see it. (`go` passes `--merge` only after its deferred findings are settled.)
- **A merge that deploys is a deploy: ask first.** The script lists the workflows that run on push (follow any `workflow_run` chained to one). If one deploys on the default branch (EAS Update / OTA, a production web deploy, a release) and this PR's paths aren't excluded by its `paths` / `paths-ignore`, stop and ask before merging.
- **A check that never started** for account reasons isn't a diff failure, and the gate passes it only with `--verified-locally`; standalone, ask. Say it in the PR as it is: "CI 미실행(<reason>), 로컬 검사로 머지".

Then, in this order:

1. Run each `merge: retarget stacked PR first` command. Deleting a base branch auto-closes the PRs on it. Don't rebase or push their branches; say they may need a rebase.
2. Run the printed `gh pr merge` command. Its method is the one recent merges used among those the repo allows; drop `--delete-branch` when the repo's rules keep merged branches ([conventions.md](../../../references/conventions.md)).
3. Confirm with `gh pr view --json state,mergedAt`. Switch to the default branch and `git pull --ff-only` only if the tree is clean and the default branch isn't checked out in another worktree; otherwise say so.
