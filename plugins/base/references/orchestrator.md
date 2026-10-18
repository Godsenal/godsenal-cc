# Orchestrator contract

How a program that runs agents with no person attached (for example `claude -p` started by a daemon) plugs gbase skills into its own steps. The contract is environment variables, files, report lines, and the manifest `.claude-plugin/factory.json`. With none of the variables set, every skill behaves as it does interactively.

## Environment

| Variable | Values | Read by | Effect |
|---|---|---|---|
| `AGENT_HEADLESS` | `1` | every skill that would ask | No questions; see [headless.md](headless.md). |
| `AGENT_ASK_CMD` | a shell command line | the same, only under `AGENT_HEADLESS=1` | Questions go to this command; protocol in [headless.md](headless.md#agent_ask_cmd). |
| `AGENT_SHIP_OWNER` | `orchestrator`, `agent` | `go` | `orchestrator`: `go` stops after local commits and a PR body draft. Unset or any other value: `agent`, today's flow (push, PR, monitor). |
| `AGENT_PR_BODY_FILE` | a path | `go` when the owner is `orchestrator` | Where the draft goes. Default `$(git rev-parse --absolute-git-dir)/gbase/pr-body.md` (per worktree, outside the tree). |
| `AGENT_EVIDENCE_FILE` | a path | `go`, `reproduce` | Check results are appended as JSON lines ([below](#evidence-file)). |

## Report lines

The final assistant message carries these lines at column 0; grep for the prefix.

- `결정 필요: …` — a decision taken without a person, or an irreversible step not taken ([headless.md](headless.md#결정-필요-lines)).
- `ship: local <branch> @<short-sha> — <n> commits, not pushed` — `go` under `AGENT_SHIP_OWNER=orchestrator`.
- `PR 본문 초안: <absolute path>` — the same run.
- `settle: …` — `monitor --until-settled` ([below](#settle)).

## Ship owner `orchestrator`

`go` runs review ∥ polish, applies review fixes, and runs its verification gate as usual. A clean tree targets every commit on the branch that isn't in the base, since the orchestrator's agent may have committed as it worked. Then `branch-pr` runs in local mode. It commits on the current branch, and creates a branch only when the current one is the default branch. It never pushes, opens a PR, uploads images, or starts `monitor`. It writes the PR draft:

- line 1: the PR title
- line 2: empty
- line 3 on: the body exactly as `gh pr create --body` would receive it — `## Why`, `## Change outline`, `## Evidence`, `## Merge danger`, `## Rollout / Deploy order` when compat-check returned `⚠️ Requires ordered rollout`, `## Notes`. Screenshots are referenced by their local `artifacts/verify/…` path, because nothing was uploaded.

Opening the PR from it: `gh pr create --title "$(head -n 1 "$f")" --body "$(tail -n +3 "$f")"`. Review findings that needed a decision are in the report as a table, under `## Notes` in the draft, and in the evidence file as a failed `review` line.

## Evidence file

JSON Lines, appended with `>>`, never rewritten (the caller may have written lines first). One object per line:

| Field | Required | Value |
|---|---|---|
| `step` | yes | `review`, `polish`, `checks`, `behavior`, `reproduce` |
| `result` | yes | `pass`, `fail`, `skip` |
| `command` | yes | what ran: the shell command for `checks` and `reproduce`; the skill and feature for `behavior` (`/verify login`); the skill for `review` and `polish` |
| `detail` | yes | one line, at most ~500 characters: on `fail` the lines that show the failure, on `skip` the reason, on `pass` what was observed |
| `cause` | on `checks`/`behavior` `fail` | `diff` (the change caused it), `pre-existing`, `flaky`, or `environment` (no DB, device, or credential) |

Lines per step:

- `review` — one per `go` run. `pass`: the review ran and no surviving finding is left open. `fail`: findings that need a decision remain; `detail` lists `severity file:line`. `skip`: not run (`--no-review`, a scope review skips, or the finder never returned).
- `polish` — one per `go` run. `fail` only when polish couldn't complete; a reverted edit isn't a failure.
- `checks` — one per verification command, with its final result after any fix attempts. `--no-verify` or no commands found → one `skip` line.
- `behavior` — one per feature the repo's verify skill drove. No verify skill, or no touched feature in its map → one `skip` line.
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
      "reads": ["<path or glob in the target repo>"]
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

A slot the manifest doesn't list isn't supplied; an orchestrator ignores slots it doesn't know. There is no `plan` slot: `gbase:how` explains the code a task touches, but it doesn't decide scope or acceptance criteria.
