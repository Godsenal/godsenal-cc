# Running workers

Read this when a change splits into two or more independent code units. A single unit is built in the main session.

## Launch

- One `subagent_type: "gbase:worker"` per unit, all in one message, with `run_in_background: true` and `isolation: "worktree"`.
- Brief each with the unit, its check, and file pointers, not pasted context.
- Workers see only committed `HEAD`, not your uncommitted edits: paste any shared shape they depend on into each brief, and keep units off files you've changed.

## Take the changes back

Take each change as a patch, without commits (no hooks to fail):

```bash
git -C <wt> add -A && git -C <wt> diff --cached --binary | git apply
```

Read the patch, then run the checks once on the whole. Clean up each worktree:

```bash
git worktree remove --force <wt> && git branch -D <its branch>
```
