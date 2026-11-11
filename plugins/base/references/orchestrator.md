# Orchestrator contract

How a program that runs agents with no person attached (for example `claude -p` started by a daemon) plugs gbase skills into its own steps. The contract is environment variables, files, report lines, and the manifest `.claude-plugin/factory.json`. With none of the variables set, every skill behaves as it does interactively.

## Environment

| Variable | Values | Read by | Effect |
|---|---|---|---|
| `AGENT_HEADLESS` | `1` | every skill that would ask | No questions; see [headless.md](headless.md). |
| `AGENT_ASK_CMD` | a shell command line | the same, only under `AGENT_HEADLESS=1` | Questions go to this command; protocol in [headless.md](headless.md#agent_ask_cmd). |
| `AGENT_SHIP_OWNER` | `orchestrator`, `agent` | `go`, `monitor --until-settled` | `orchestrator`: `go` stops after local commits and a PR body draft; `monitor --until-settled` commits its fixes locally and posts nothing ([Settle](#settle)); other `monitor` modes aren't run under it. Unset or any other value: `agent` — `go` pushes, opens the PR and reports `pr: <url>`; under `AGENT_HEADLESS=1` it then runs `monitor --until-settled` and ends with its `settle:` line instead of watching to merge. |
| `AGENT_PR_BODY_FILE` | a path | `go` and `monitor --until-settled` when the owner is `orchestrator` | Where the draft goes. Default `$(git rev-parse --absolute-git-dir)/gbase/pr-body.md` (per worktree, outside the tree). |
| `AGENT_EVIDENCE_FILE` | a path | `go`, `reproduce`, `monitor --until-settled` | Check results are appended as JSON lines ([below](#evidence-file)). |

## Report lines

The final assistant message carries these lines at column 0; grep for the prefix.

- `결정 필요: …` — a decision taken without a person, or an irreversible step not taken ([headless.md](headless.md#결정-필요-lines)).
- `ship: local <branch> @<short-sha> — <n> commits, not pushed` — `go` under `AGENT_SHIP_OWNER=orchestrator`, and `monitor --until-settled` under it when it committed fixes.
- `PR 본문 초안: <absolute path>` — the same runs.
- `ship: skip — <reason>` — a run whose caller put shipping out of scope ("do not push"); it carries no `결정 필요:` line about it ([headless.md](headless.md#결정-필요-lines)).
- `pr: <url>` — `branch-pr` after `gh pr create`, carried up by `go`: the PR an agent-owned run opened.
- `settle: …` — `monitor --until-settled` ([below](#settle)).
- `남은 작업: <task>` — `gbase:work` when the task was more than one PR's worth: a slice it left for a later run, one line each, complete enough to be that run's task. The caller starts them as new `work` runs, in order when one depends on another.
- `mockup: <index.html>`, `mockup url: <url> | none — <reason>`, `mockup shots: <dir>` — `gbase:mockup`.
- `교훈: <target skill> — <date "user's words">: <rule>` — gshorts' `content-common` feedback intake: a lesson for the harness. A content run never edits the harness source (`plugins/…` of any checkout) itself; a `work` run ships the lines, reviewed, as a PR ([Runner](#runner) prints the command).

Relaying a run's result to a person, a bot puts `gbase-run cite <run-id>` (the run's `provenance`) on the first or last line of the message: `Claude Code · opus · 계정 default · run 20261102-235341-work-bae706 · 스킬 gbase:work→go`. Something the bot read or checked itself is marked `봇 직접` instead. Without it people ask whether Claude Code really did it, and the work gets done twice (2026-10-30 through 11-02). A bot that still runs `claude -p` itself writes its `.ACCOUNT` file as one line holding only the account name used in `GBASE_ACCOUNTS` (`default`, `c5`), not `ACCOUNT=default` or a path.

## Ship owner `orchestrator`

`go` runs review ∥ polish, applies review fixes, and runs its verification gate as usual. A clean tree targets every commit on the branch that isn't in the base, since the orchestrator's agent may have committed as it worked. Then `branch-pr` runs in local mode. It commits on the current branch, and creates a branch only when the current one is the default branch. It never pushes, opens a PR, uploads images, or starts `monitor`. It writes the PR draft:

- line 1: the PR title
- line 2: empty
- line 3 on: the body exactly as `gh pr create --body` would receive it — `## Why`, `## Review focus`, `## Change outline`, `## Evidence`, `## Rollout / Deploy order` when compat-check returned `⚠️ Requires ordered rollout`, `## Notes`. Nothing was uploaded, so each screenshot is embedded as `![<label>](<absolute local path>)`: upload those files and rewrite the links before opening the PR, or the reviewer sees broken images.

Opening the PR from it: `gh pr create --title "$(head -n 1 "$f")" --body "$(tail -n +3 "$f")"`. Review findings that needed a decision are in the report as a table, under `## Review focus` in the draft, and in the evidence file as an `open` `review` line.

## Evidence file

JSON Lines, appended with `>>`, never rewritten (the caller may have written lines first). One object per line:

| Field | Required | Value |
|---|---|---|
| `step` | yes | `review`, `polish`, `checks`, `behavior`, `reproduce`, `settle` |
| `result` | yes | `pass`, `fail`, `skip`, `open` (`review`, `settle`, and `reproduce` only: ran, but something awaits a decision or hasn't concluded — not a failure) |
| `command` | yes | what ran: the shell command for `checks` and `reproduce`; the skill and feature for `behavior` (`/verify login`); the skill for `review` and `polish` |
| `detail` | yes | one line, at most ~500 characters: on `fail` the lines that show the failure, on `skip` the reason, on `pass` what was observed, on `open` what is left |
| `cause` | on `checks`/`behavior` `fail`, `reproduce` `open` | `diff` (the change caused it), `pre-existing`, `flaky`, or `environment` (no DB, device, or credential); on `reproduce` `open`: `input differs from report — <difference>` |
| `input` | no | what the check ran on, when that's a choice: a fixture, a sample file, a simulator, a seed (`fixture same-scene-1028, 1024px messenger copies`). When it differs from what the bug report or real use has in a way the result could hang on (resolution, format, metadata, size, device), end it with `; differs: <difference>` (`; differs: device photos are 5712×4284 originals without EXIF`) |

Lines per step:

- `review` — one per `go` run, and per `monitor --until-settled` run whose self-review ran. `pass`: the review ran and no surviving finding is left open. `open`: findings that need a decision remain; `detail` lists `severity file:line`. (Before v1.28.0 this was `fail`; a reader of older files should treat a `review` `fail` as `open`.) `skip`: not run (`low` risk, `--no-review`, a scope review skips, or the finder never returned).
- `polish` — one per `go` run. `fail` only when polish couldn't complete; a reverted edit isn't a failure.
- `checks` — one per verification command, with its final result after any fix attempts. `--no-verify` or no commands found → one `skip` line.
- `behavior` — one per feature checked on its surface: by the repo's verify skill, by a CLI or script run when there is none (`command` is then that shell command), or reused from `gbase:work`'s route run. `low` risk, or nothing that could be run → one `skip` line.
- `settle` — one per `monitor --until-settled` run: `pass` for `수렴`, `open` for `미확정`, `fail` for `사람 필요`; `detail` is the `settle:` line. Its fix verifications are `checks` lines.
- `reproduce` — the result of the reproduction check now: `fail` means the bug reproduced or the criterion isn't met, `pass` means it didn't reproduce, `skip` means no executable check was possible, `open` means it didn't reproduce on an input of another kind than the report's (`cause` says how they differ).

Write each line with a JSON encoder, never by hand-quoting:

```bash
python3 -c 'import json,sys; k="step","result","command","detail","cause","input"; print(json.dumps({a:b for a,b in zip(k,sys.argv[1:]) if b}, ensure_ascii=False))' \
  checks fail 'pnpm vitest run src/auth' 'auth.test.ts: expected 200, received 500' diff >> "$AGENT_EVIDENCE_FILE"
```

A `checks` or `behavior` line whose `input` says `differs:` becomes a `(확인)` item in the PR's `## Review focus` (`실기기 확인 필요: <difference>`): passing on a fixture says nothing about the input that failed.

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

When more than one applies, `사람 필요` wins over `미확정`. The head sha is the last one monitor waited on; each fix it pushes starts a new wait. It never merges in this mode, and rebases (pushing with `--force-with-lease`) only when the invocation explicitly asks to rebase ([monitor](../skills/monitor/SKILL.md#--until-settled)); otherwise it never rebases or force-pushes. Wherever monitor does resolve a conflict, a resolution that combined both sides' content is reviewed before it's pushed, or leaves a `review` `open` evidence line ([monitor's Conflicts](../skills/monitor/SKILL.md#conflicts)).

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
- `slots.<slot>.model` — optional: the model the slot runs on unless the caller names one. Slots that make the judgment calls are `opus`; slots that carry out a change already made (`ship`, `settle`, …) are `sonnet`; `task` has none, so the caller's or the account's default applies.
- `slots.<slot>.models` — optional: run `invoke` once per model, in independent sessions at the same time, and merge their reports. Only `review2` has it: `gbase:review` in *report only* mode, so neither session edits the tree, merged by `file:line` (same file, lines at most 3 apart) with each finding marked by the model(s) that found it.

`content` names a skill of the gshorts plugin in this marketplace (`/gshorts:content-common`), so its caller loads gshorts too (the runner does). `task` has no skill: its `invoke` is a bare `<task>`, so the prompt is the task, run under the same runner for its log, result, stop, and notify. No skill loads [headless.md](headless.md) in it, so the runner appends a short paragraph of its rules: no questions, the `결정 필요:` format, and the steps never taken on a guess (including evidence-less 약관·법적 동의, 대표자·본인 확인 체크, and 사실 진술 boxes).

`work` is the dev run's entry: an orchestrator that opens a task with `/gbase:work <task>` gets the whole route, ending in `go`, so it lists no review, polish or checks steps of its own. With `AGENT_SHIP_OWNER=agent` the run also pushes and opens the PR (`pr:` line), then settles it (`settle:` line); it never merges. Under `AGENT_HEADLESS=1` `go` reviews every tier before the PR, `low` included. Tasks that touch the same files — harness rule updates, the lessons of several content runs — go into one `work` run: two runs on the same skills at once made two PRs, and the second one's conflict was resolved without a review.

A slot the manifest doesn't list isn't supplied; an orchestrator ignores slots it doesn't know. There is no `plan` slot: `gbase:how` explains the code a task touches, but it doesn't decide scope or acceptance criteria.

## Runner

`scripts/gbase-run` in this repo is one way to be the caller: it runs a single slot with `claude -p` and leaves a result file (`result.json`) for a poller. Its commands, run directory, and result fields are in [runner.md](runner.md) — a skill never needs that file.
