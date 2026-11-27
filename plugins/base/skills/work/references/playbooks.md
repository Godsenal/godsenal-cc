# Following a pstack playbook under `work`

Read once per session, before the first playbook. The playbooks in `../../poteto-mode/playbooks/` are generated copies of pstack's (never edited here), written for Cursor and for pstack on its own. Follow their steps with these changes; where a playbook and `work` differ, `work` wins.

| The task is | Its playbook in `../../poteto-mode/playbooks/` |
|---|---|
| New or changed behavior | `feature.md` |
| Structure changes, behavior doesn't | `refactoring.md` |
| A measured slowness | `perf-issue.md` |
| A capture to diagnose: a CPU profile, trace, heap snapshot, spindump | `trace-forensics.md` |
| A live process that spins, leaks, or glitches, no capture yet | `runtime-forensics.md` |
| One metric pushed to a target over many tries; a port that must look identical; a blind comparison of skills or prompts | `hillclimb.md`; `visual-parity.md`; `eval.md` |
| A decision to make cheaply (which layout, which approach) | `prototype.md`. It doesn't ship. |
| "Until X passes", "keep going", unattended | `autonomous-run.md` |
| Phased work spread over several PRs | `multi-phase-plan.md` for the plan file. A task that also asks for the first phase builds that PR by its own row; the rest are `남은 작업:` lines. |

No row fits → say so and plan the steps under [principles.md](principles.md).

- **A step that commits, pushes, opens, watches, or merges a PR is `work`'s Ship** ("Run Opening a PR", "commit liberally", "rebase into small ordered commits", "stage the commits so the failing repro lands first", "babysit"). Make no commits along the way, and where a playbook reverts a failed try, undo your own edit (never `git checkout` a file that holds accepted work): `branch-pr` groups the change into commits, and PR format comes from [conventions.md](../../../references/conventions.md).
- **"Trace the affected subsystem"** is `gbase:how`, skipped when the task names the files and the shape (`skip: the task names the files`).
- **"The control skill", "the matching surface"** is the repo's verify skill (`.claude/skills/verify-*/` or `.claude/skills/verify/`), else the CLI or the screen itself. Type check and tests alone are not the surface.
- **"Delegate to a subagent"** follows `work`'s subagent rule ([workers.md](workers.md)): `gbase:worker` for code, `gbase:scout` for reading, no `model`, no reasoning level. A single unit, a design call, or units that write the same files stay in the main session, even where the playbook calls delegation mandatory.
- **A skill a step names** (`architect`, `arena`, `interrogate`, `swarm`, `tdd`, `show-me-your-work`, a `principle-*`) is read at `../../<name>/SKILL.md` when that step is reached and the call it settles is still open. A shape the task already gives skips it with the reason. `/loop` is the session's `loop` skill when it has one.
- **A "throughput checkpoint"** stays as the playbook writes it: four todo items, or the one `n/a` line.
- **A question a playbook would ask** follows `work`'s Headless section, and a step that "waits for the operator" is a `결정 필요:` line in a headless run.
- **`multi-phase-plan.md` ends at the plan file** ("Do not implement"). When the task also asks for the first phase, build that one PR by its own route after the plan is written; every later phase is a `남은 작업:` line that names the plan file.
- Any other Cursor name (`Task`, `AskQuestion`, a model slug, Bugbot, cloud agents): [pstack-adapter.md](../../../references/pstack-adapter.md).

Playbooks `work` doesn't route to, because a gbase skill does the job: `bug-fix.md` (`gbase:bug-fix`), `investigation.md` (`gbase:how` / `gbase:why`), `opening-a-pr.md`, `shipping.md`, `babysit.md` (`gbase:go`, `gbase:monitor`), `session-pickup.md` (`gbase:pickup`), `pause-safely.md` (`gbase:pause`), `authoring-a-skill.md` (the target repo's own skill rules). `autopilot-full.md` and `autopilot-stack.md` have each PR's owner merge on its own verdict; here every PR is its own `work` run from a `남은 작업:` line.
