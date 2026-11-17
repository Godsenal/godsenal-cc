# Pre-PR review: Steps 2 and 3 on `medium` and `high`

Read before Step 2 when the risk is `medium` or `high` (and on `low` in a headless run, by orchestrated.md). Review runs before the PR so its fixes land in the initial commits; a review after the PR opens turns every finding into an extra commit and a CI rerun.

## Step 2: the finder, in the same message as polish

```
Agent(subagent_type: "general-purpose", run_in_background: true, description: "review finder",
      prompt: "Run Skill(skill: \"code-review\", args: \"<effort> <scope from Step 1>\") and return its findings verbatim. Edit nothing.")
```

- **Don't call `code-review` in the main session.** Under `claude -p` a forked skill blocks its caller until it finishes, which turned review ∥ polish into review → polish.
- **Pass the scope explicitly.** With no target the built-in reviews the current diff, which is empty on the clean-tree path: it would report "nothing found" about a commit it never read.
- Effort per Step 1's table, never above `high`: above `medium` the built-in already fans out to a multi-agent workflow.
- Never `--fix` (it would race polish for the same files), `--comment` (no PR yet), or `ultra` (user-triggered and billed).

## Step 3: judge and fix

If the findings haven't arrived when polish finishes, wait for them: the gate then runs once on the final tree. If the finder fails, go on without it (Step 6 drops `--no-review`). Then hand the findings to review's judgment stages, in a subagent:

```
Agent(subagent_type: "general-purpose", run_in_background: false, description: "review",
      prompt: "In <repo path>, run Skill(skill: \"gbase:review\", args: \"pre-PR mode; defer, don't ask; candidates already found — start at Stage 2. Findings: <finder output>\") and return its table and tally line verbatim. Polish rewrote these files after the findings were written: locate each finding by the code it quotes, not by file:line, and re-judge any whose quoted code is gone. Where a fix and a polish edit collide, the fix wins.")
```

On `medium`, insert `; one skeptic for low/medium` right after `start at Stage 2`. No `Agent` tool in this session → call `gbase:review` directly with the same args.

Clear fixes come back as working-tree edits (no commits: `branch-pr` groups them); judgment calls come back deferred. Read `git diff --stat` to see what the agents changed, then tally in one line: `review: F found, R refuted, S survived — A fixed, K deferred`. Go on to Step 4 in the same turn: under `claude -p` a turn that ends on the table ends the run once no background task is left to wake it.
