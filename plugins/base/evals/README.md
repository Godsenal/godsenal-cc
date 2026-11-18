# gbase evals

Checks that `gbase:work` loads `gbase:design-taste` when it should and skips it when it shouldn't, that it ships through `gbase:go`, that a small fix stays light, that a headless run reports the slices it left, that a route reads its pstack playbook, and that `gbase:go`'s polish step audits the comments a change added.

| case | expects |
|---|---|
| `screen-loads-design-taste` | a screen change loads `design-taste` before the first `Edit` |
| `figma-given-skips-design-taste` | a task that hands over a Figma design does not load it |
| `logic-only-skips-design-taste` | a logic-only edit inside a UI file does not load it |
| `chore-ships-through-go` | a one-line chore asked as "a quick PR" loads `gbase:go` and runs no `git commit`/`push`/`gh pr` by hand |
| `small-fix-skips-playbooks` | a one-header fix edits the file and reads no pstack playbook, principle skill, or deep-procedure skill |
| `headless-reports-remaining-slices` | a headless task holding two PRs' worth asks nothing and reports the second as a `남은 작업:` line |
| `trace-artifact-reads-forensics` | a CPU-profile diagnosis reads `poteto-mode/playbooks/trace-forensics.md` (failed before 1.56.0, when `work` had no route to the playbooks) |
| `phased-work-reads-multi-phase-plan` | a phased task reads `poteto-mode/playbooks/multi-phase-plan.md` (failed before 1.56.0) |
| `comments-audited-on-ship` | `go` on a change with a narrating comment and a workaround comment passes polish `risk: <tier>`, a `gbase:comment-sicko` agent runs, and both comments are gone from the file (failed before 1.58.0, when polish had no comment pass) |
| `comments-none-skips-audit` | the same change without comments launches polish and no `gbase:comment-sicko` agent |
| `comments-headless-keeps-constraint-open` | a headless `go` on a change with a `DO NOT REMOVE` comment asks nothing, deletes the comment, adds no test or lint config, and reports the constraint on a `결정 필요:` line (failed before 1.58.0) |

Run from `plugins/base` (8 cases at 3 runs each took about 13 minutes and $6; there are 11 now):

```bash
claude plugin eval . --ablation none --scaffold --trust-plugin --allow-tools Edit Write --no-publish --threshold 0.67
```

- Keep the results out of the repo: add `--output-dir <dir outside the plugin> --json <file>.json` (the default writes `evals/results/<timestamp>/`, which is not committed).
- Run one case only: add `--case <name>` (a name glob, e.g. `--case chore-ships-through-go`).
- Change the number of runs per case: add `--runs <n>` (default: the case's `runs` if set, else 3).

Seen on 1.44.2: `screen-loads` and `logic-only` passed every run; `figma-given` passed 8 of 10 runs, so read its score as a rate, not a gate.

Limit: an eval run loads only this plugin. gbase 1.44.0, which had no design-taste step in `work`, also passed `screen-loads-design-taste` 3 of 3 here, while 22 real work runs that edited UI files with `design-taste` available (136–156 skills in the session) loaded it 0 times. So this suite guards the three behaviors against regressions; it does not reproduce the crowded-session miss. Check that one in real runs: `skills` in `result.json`.

Seen on 1.55.0 (2026-11-17, 3 runs per case): the first six cases above passed every run except one `screen-loads` run (it loaded `design-taste` after its first edit; 6 more runs of that case all passed, as did 9 of 9 on 1.54.0), and both playbook cases failed every run, as expected before `work` routes to them. The cases allow no `Bash`, so they cover `work`'s routing only. `branch-pr` and `monitor` are checked by `scripts/test_ship_prep.py` and `scripts/test_pr_status.py`, and by running them with `claude -p --plugin-dir plugins/base` in a scratch repo with a fake `gh`.

Seen on 1.56.0 (2026-11-17, 3 runs per case, 252 seconds, $7.16, on the final tree; a run on an earlier draft scored the same): all eight cases passed every run, the two playbook cases included. The same suite on 1.55.0 an hour earlier (224 seconds, $5.96): six cases 3 of 3, both playbook cases 0 of 3. `go`'s subagent steps (polish, review, compat-check, unslop) need `Bash` and `Agent`, so they are not covered here: check them with `claude -p "/gbase:go" --plugin-dir plugins/base` in a scratch repo, with `AGENT_HEADLESS=1 AGENT_SHIP_OWNER=orchestrator` so nothing is pushed.

The three `comments-*` cases run `/gbase:go --no-review --no-verify` with shipping out of scope, so they need `Bash` and `Agent` (`--allow-tools Bash Edit Write`; `Agent` is in each case's `allowed_tools`). The graders count tool calls made by subagents too: the `gbase:comment-sicko` launch is two levels down, inside the polish agent. `git` does not run in the eval sandbox (its `xcrun` shim can't write a cache file), so `added-comments` exits with `next: read the diff yourself` there and the agent decides by reading the file; the script's own decisions are covered by `scripts/test_added_comments.py`. An eval case can set only `EVAL_*` variables, so these prompts say "헤드리스" in words, as `headless-reports-remaining-slices` does.

Seen on 1.58.0 (2026-11-18, the three `comments-*` cases, 3 runs each, `-j 3`, about 375 seconds and $8 a suite). On 1.57.7 (310 seconds, $6.54): `comments-audited-on-ship` 0 of 3 (no `risk:` passed, no comment agent, the workaround comment left in), `comments-headless-keeps-constraint-open` 0 of 3 (the constraint comment left in every run), `comments-none-skips-audit` 3 of 3. On 1.58.0, `comments-audited-on-ship` and `comments-none-skips-audit` passed every run of three suites (9 of 9 each). `comments-headless-keeps-constraint-open` is a rate, not a gate: polish deleted the comment and wrote its `결정 필요:` line in every run read, but `go`'s main session sometimes put the comment back or rewrote the line as a heading with bullets. A first draft failed 0 of 3 that way; with "a comment polish deleted stays deleted" in `go`'s Step 2 it passed 6 of 10; with the caller note polish now writes above its lines it passed 5 of 6. The one failure restored the comment on purpose, citing `headless.md`'s "never the option that deletes".
