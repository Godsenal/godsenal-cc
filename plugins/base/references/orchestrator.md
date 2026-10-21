# Orchestrator contract

How a program that runs agents with no person attached (for example `claude -p` started by a daemon) plugs gbase skills into its own steps. The contract is environment variables, files, report lines, and the manifest `.claude-plugin/factory.json`. With none of the variables set, every skill behaves as it does interactively.

## Environment

| Variable | Values | Read by | Effect |
|---|---|---|---|
| `AGENT_HEADLESS` | `1` | every skill that would ask | No questions; see [headless.md](headless.md). |
| `AGENT_ASK_CMD` | a shell command line | the same, only under `AGENT_HEADLESS=1` | Questions go to this command; protocol in [headless.md](headless.md#agent_ask_cmd). |
| `AGENT_SHIP_OWNER` | `orchestrator`, `agent` | `go`, `monitor --until-settled` | `orchestrator`: `go` stops after local commits and a PR body draft; `monitor --until-settled` commits its fixes locally and posts nothing ([Settle](#settle)); other `monitor` modes aren't run under it. Unset or any other value: `agent`, today's flow (push, PR, monitor, replies). |
| `AGENT_PR_BODY_FILE` | a path | `go` and `monitor --until-settled` when the owner is `orchestrator` | Where the draft goes. Default `$(git rev-parse --absolute-git-dir)/gbase/pr-body.md` (per worktree, outside the tree). |
| `AGENT_EVIDENCE_FILE` | a path | `go`, `reproduce`, `monitor --until-settled` | Check results are appended as JSON lines ([below](#evidence-file)). |

## Report lines

The final assistant message carries these lines at column 0; grep for the prefix.

- `결정 필요: …` — a decision taken without a person, or an irreversible step not taken ([headless.md](headless.md#결정-필요-lines)).
- `ship: local <branch> @<short-sha> — <n> commits, not pushed` — `go` under `AGENT_SHIP_OWNER=orchestrator`, and `monitor --until-settled` under it when it committed fixes.
- `PR 본문 초안: <absolute path>` — the same runs.
- `settle: …` — `monitor --until-settled` ([below](#settle)).

## Ship owner `orchestrator`

`go` runs review ∥ polish, applies review fixes, and runs its verification gate as usual. A clean tree targets every commit on the branch that isn't in the base, since the orchestrator's agent may have committed as it worked. Then `branch-pr` runs in local mode. It commits on the current branch, and creates a branch only when the current one is the default branch. It never pushes, opens a PR, uploads images, or starts `monitor`. It writes the PR draft:

- line 1: the PR title
- line 2: empty
- line 3 on: the body exactly as `gh pr create --body` would receive it — `## Why`, `## Change outline`, `## Evidence`, `## Merge danger`, `## Rollout / Deploy order` when compat-check returned `⚠️ Requires ordered rollout`, `## Notes`. Screenshots are referenced by their local `artifacts/verify/…` path, because nothing was uploaded.

Opening the PR from it: `gh pr create --title "$(head -n 1 "$f")" --body "$(tail -n +3 "$f")"`. Review findings that needed a decision are in the report as a table, under `## Notes` in the draft, and in the evidence file as an `open` `review` line.

## Evidence file

JSON Lines, appended with `>>`, never rewritten (the caller may have written lines first). One object per line:

| Field | Required | Value |
|---|---|---|
| `step` | yes | `review`, `polish`, `checks`, `behavior`, `reproduce`, `settle` |
| `result` | yes | `pass`, `fail`, `skip`, `open` (`review` and `settle` only: ran, but something awaits a decision or hasn't concluded — not a failure) |
| `command` | yes | what ran: the shell command for `checks` and `reproduce`; the skill and feature for `behavior` (`/verify login`); the skill for `review` and `polish` |
| `detail` | yes | one line, at most ~500 characters: on `fail` the lines that show the failure, on `skip` the reason, on `pass` what was observed, on `open` what is left |
| `cause` | on `checks`/`behavior` `fail` | `diff` (the change caused it), `pre-existing`, `flaky`, or `environment` (no DB, device, or credential) |

Lines per step:

- `review` — one per `go` run, and per `monitor --until-settled` run whose self-review ran. `pass`: the review ran and no surviving finding is left open. `open`: findings that need a decision remain; `detail` lists `severity file:line`. (Before v1.28.0 this was `fail`; a reader of older files should treat a `review` `fail` as `open`.) `skip`: not run (`--no-review`, a scope review skips, or the finder never returned).
- `polish` — one per `go` run. `fail` only when polish couldn't complete; a reverted edit isn't a failure.
- `checks` — one per verification command, with its final result after any fix attempts. `--no-verify` or no commands found → one `skip` line.
- `behavior` — one per feature the repo's verify skill drove. No verify skill, or no touched feature in its map → one `skip` line.
- `settle` — one per `monitor --until-settled` run: `pass` for `수렴`, `open` for `미확정`, `fail` for `사람 필요`; `detail` is the `settle:` line. Its fix verifications are `checks` lines.
- `reproduce` — the result of the reproduction check now: `fail` means the bug reproduced or the criterion isn't met, `pass` means it didn't reproduce, `skip` means no executable check was possible.

Write each line with a JSON encoder, never by hand-quoting:

```bash
python3 -c 'import json,sys; k="step","result","command","detail","cause"; print(json.dumps({a:b for a,b in zip(k,sys.argv[1:]) if b}, ensure_ascii=False))' \
  checks fail 'pnpm vitest run src/auth' 'auth.test.ts: expected 200, received 500' diff >> "$AGENT_EVIDENCE_FILE"
```

## Settle

`/gbase:monitor --until-settled` judges the PR's current head and ends instead of waiting for a merge. It ends with exactly one line:

```
settle: 수렴 @<short-sha>
settle: 미확정 @<short-sha> — 안 옴: <check or reviewer>, …
settle: 사람 필요 @<short-sha> — <item>, …
```

- `수렴` — every check on the head concluded without failure, every expected automated reviewer finished on it, and nothing monitor handles is left open.
- `미확정` — something hadn't concluded 30 minutes into the wait on this head.
- `사람 필요` — something only a person can resolve: a failing check monitor couldn't fix, a review comment that needs a decision, a standing `CHANGES_REQUESTED`, or a merge conflict.

When more than one applies, `사람 필요` wins over `미확정`. The head sha is the last one monitor waited on; each fix it pushes starts a new wait. It never merges, rebases, or force-pushes in this mode.

Under `AGENT_SHIP_OWNER=orchestrator` (the runner's default) monitor pushes nothing and posts nothing. It judges the pushed head once, commits its fixes locally, and, when there are any, writes an updated PR draft to `AGENT_PR_BODY_FILE` and ends with `ship: local …`, `PR 본문 초안: …`, and `settle: 미확정 @<pushed sha> — 푸시 대기: <n> commits` (or `사람 필요`). The caller pushes, updates the PR body from the draft (`gh pr edit --title "$(head -n 1 "$f")" --body "$(tail -n +3 "$f")"`), and runs settle again. `AGENT_SHIP_OWNER=agent` opts into pushing and replying.

## Manifest

`.claude-plugin/factory.json` names what this plugin supplies for each slot an orchestrator may have. The plugin's version is in `plugin.json` next to it.

```json
{
  "schema": 1,
  "contract": "references/orchestrator.md",
  "env": { "<VARIABLE>": "<what it does>" },
  "slots": {
    "<slot>": {
      "invoke": "<slash command>",
      "env": ["<VARIABLE>"],
      "notes": "<what it returns and what it leaves behind>",
      "setup": "<slash command>",
      "reads": ["<path or glob in the target repo>"],
      "models": ["<model>", "<model>"]
    }
  }
}
```

- `schema` — an integer, raised when the shape changes incompatibly.
- `contract` — this document, relative to the plugin root.
- `env` — every variable any slot reads, each with a one-line meaning.
- `slots.<slot>.invoke` — the prompt that fills the slot, or `null` when the slot is a file in the target repo rather than a command (`reads` says which).
- `slots.<slot>.env` — the variables that invocation reads; each is a key of `env`.
- `slots.<slot>.notes` — what the caller gets back and what is left in the working tree.
- `slots.<slot>.setup` — optional: the command that creates what the slot depends on in a target repo.
- `slots.<slot>.reads` — optional: target-repo files the slot depends on.
- `slots.<slot>.models` — optional: run `invoke` once per model, in independent sessions at the same time, and merge their reports. Only `review2` has it: `gbase:review` in *report only* mode, so neither session edits the tree, merged by `file:line` (same file, lines at most 3 apart) with each finding marked by the model(s) that found it.

A slot the manifest doesn't list isn't supplied; an orchestrator ignores slots it doesn't know. There is no `plan` slot: `gbase:how` explains the code a task touches, but it doesn't decide scope or acceptance criteria.

## Runner

`scripts/gbase-run` in this repo is one way to be the caller: it runs a single slot with `claude -p` and leaves a result file for a poller. It reads the manifest and this contract and adds no skill behavior.

```
gbase-run --repo <path> --slot <slot> [--task "..."] [--worktree <name>] [--model opus|sonnet]
          [--ship-owner orchestrator|agent] [--answers <file>]
gbase-run status <run-id>
gbase-run list
```

- The prompt is the slot's `invoke`, with `--task` replacing a `<placeholder>` or appended. A slot whose `invoke` is `null` gets a prompt built from its `notes`.
- The child runs with `AGENT_HEADLESS=1`, `AGENT_SHIP_OWNER` from `--ship-owner` (default `orchestrator`, so nothing leaves the machine), `AGENT_PR_BODY_FILE` and `AGENT_EVIDENCE_FILE` in the run directory, `GITHUB_TOKEN` removed, and the plugin loaded with `--plugin-dir` from the same checkout. `AGENT_ASK_CMD` is `$GBASE_ASK_CMD` when set; otherwise `gbase-run question <run-id>`, which records each question in `questions.jsonl` and gives no answer, so the skill applies its recommendation and writes a `결정 필요:` line.
- `--model` is passed to claude; a `models` slot ignores it and runs its own list.
- `--worktree <name>` runs in `$GBASE_HOME/worktrees/<repo>-<path hash>-<name>` on branch `gbase/<name>`, created from the repo's `HEAD` on first use and reused after.
- The last stdout line is the absolute path of `result.json`. Exit 0 when every session exited 0. SIGTERM or SIGINT stops the claude sessions and still writes the result (`failed`, with `stopped_by`).
- A slot whose `invoke` has a `<placeholder>` (`reproduce`) needs `--task`.

Run directory `$GBASE_HOME/runs/<run-id>/` (`GBASE_HOME` defaults to `~/.gbase`): `prompt.txt`, `log.jsonl` (the `stream-json` events; `log-<model>.jsonl` per session for a `models` slot), `final.md` (the final message; `final-<model>.md`), `evidence.jsonl`, `pr-body.md` when `go` drafted one, `questions.jsonl`, `answers.json`, `review.md` for a `models` slot, and `result.json`:

| Field | Value |
|---|---|
| `run_id`, `slot`, `task`, `repo`, `cwd`, `worktree`, `model`, `ship_owner` | the inputs; `cwd` is where claude ran |
| `status` | `running` until the runner finishes, then `done` or `failed`; `status` reports `dead` for a `running` file whose runner process is gone |
| `pid`, `started_at`, `finished_at`, `run_dir`, `prompt_path`, `log_path` | bookkeeping |
| `exit_code` | the highest exit code of the claude sessions |
| `branch`, `head_sha` | of `cwd` after the run |
| `decisions` | every `결정 필요:` line, in order, as `{text, question, applied, recommend, options, human}` ([format](headless.md#결정-필요-lines)): `text` is the raw line (before v1.28.0 the list held only these strings); a part the line lacks is `null`, `options` `[]` |
| `ship`, `settle` | the `ship:` / `settle:` line, or `null` |
| `pr_body_file` | the path from `PR 본문 초안:`, else `pr-body.md` if it exists, else `null` |
| `evidence` | the parsed evidence lines |
| `questions` | each `{question, recommend, options}` sent to the default `AGENT_ASK_CMD` |
| `sessions` | per model: `session_id`, `model`, `exit_code`, `cost_usd`, `log_path`, `final_path` |
| `answers_from` | the run the answers file named; `model` is inherited from it too |
| `findings`, `report_file` | `models` slots only: `{severity, location, finding, action, found_by}` and the merged table |

A follow-up run answers a run's decisions with `--answers <file>`:

```json
{
  "run_id": "<run whose decisions these answer>",
  "answers": [
    { "decision": "<a 결정 필요: line or its question, or a question from questions.jsonl>", "answer": "<option label or instruction>" }
  ]
}
```

`run_id` is optional; when given, `--repo`, `--slot`, and `--task` default to that run's, and the run continues in that run's `cwd` (its worktree, where its edits are). The answers go into the prompt as decisions already made, and a question asked again gets its answer from `AGENT_ASK_CMD` — the exact text first, then ignoring case, a leading `결정 필요:`, and how whitespace and punctuation are spaced (`Use the cache?` matches `use the cache`; `v1.2.0` doesn't match `v12.0`). When answers that differ match only after normalizing, none is given. A `decision` that starts with `결정 필요:` is a pasted report line: only its question counts, so the `→ …` tail, the `(추천: …; 다른 선택지: …)` group, and `· AGENT_ASK_CMD 에 넘김` are dropped.

Environment of the runner itself: `GBASE_CLAUDE` (default `~/.claude/local/claude`, else `claude` on `PATH`), `GBASE_HOME`, `GBASE_PLUGIN_DIR` (default `plugins/base` of the checkout), `GBASE_PERMISSION_MODE` (default `bypassPermissions`; the child has no person to approve tools), `GBASE_ASK_CMD`.
