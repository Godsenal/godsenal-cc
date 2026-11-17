# Running workers

Read this before launching a `gbase:scout` or `gbase:worker`. Independent units are ones where neither needs the other's result and they don't write the same files; a single unit is built in the main session. Independent scouts go out several in one message.

**You own their output.** Read the diff yourself and write your own summary. Skills that dispatch their own agents (`go`, `how`, `why`) keep their types.

## Launch

- **Fresh agent per new task**, briefed with the goal, the original ask, every later instruction, and the previous agent's report. Continue an existing agent only when the work needs state that lives in it (its checkout, a running simulator or server). A second opinion is the same prompt on another model: agreement is the signal, not a persona.

- One `subagent_type: "gbase:worker"` per unit, all in one message, with `run_in_background: true` and `isolation: "worktree"`.
- Brief each with the unit, its check, and file pointers, not pasted context.
- A unit that touches what a user sees: tell the worker in its brief to run `Skill(skill: "gbase:design-taste")` before its first edit, unless the task came with a design to match (then give the worker that design). Name the stack skills the unit needs the same way. A worker doesn't inherit the skills this session loaded.
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
