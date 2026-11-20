# pstack skills in gbase

gbase carries pstack's skills (cursor/plugins, MIT, Copyright (c) 2026 Lauren Tan; license in [pstack-LICENSE](pstack-LICENSE)) as generated copies. They are written for Cursor and for pstack as a standalone plugin. Read this once per session, then apply it to every pstack skill, playbook, and agent you follow. It is gbase's version of pstack's `docs/harness/claude-code.md`; where the two differ, this file wins. If a Cursor field or step has no row here, drop it and say so.

`<root>` is this plugin's folder: two levels above any `skills/<name>/SKILL.md`, one above this file.

## Running another skill

A pstack skill names others as "the **name** skill", `/name`, or a `principle-<title>` leaf.

| The skill names | Do |
| --- | --- |
| A skill in the table below | Use the gbase skill in its row. |
| Any other pstack skill or principle | `Read` `<root>/skills/<name>/SKILL.md` (the sibling folder `../<name>/SKILL.md` of the skill you are following) and follow it. The `Skill` tool refuses these: they are user-invocable only, so they stay out of the skill listing. |
| A skill the user should type | `/gbase:<name>` |

| pstack name | In gbase |
| --- | --- |
| `how`, `why`, `unslop`, `blast-radius`, `correct` | `Skill(skill: "gbase:<name>")` |
| `create-verification-skill` | `gbase:create-verify` |
| `maintain-verification-skill` | `gbase:create-verify --maintain` |
| `/deslop` (cursor-team-kit) | `gbase:polish` |
| `control-ui`, `control-cli` (cursor-team-kit) | The repo's verify skill: `.claude/skills/verify-*/` or `.claude/skills/verify/`. None → `gbase:create-verify` can generate one; otherwise drive the app directly and say no verify skill exists. |
| `/poteto-mode`, or a task it would take | During a `gbase:work` run, stay in it: "via poteto-mode" in a playbook means by `work`'s own routes. Otherwise `Skill(skill: "gbase:work")`. `work` is poteto-mode inside gbase: its route table names the playbook to read, and `skills/work/references/playbooks.md` says how a playbook's steps change there (no commits along the way, a single unit stays in the main session). |
| Playbooks **Opening a PR**, **Shipping**, **Babysit**, and any step that commits, pushes, opens, or merges a PR | `Skill(skill: "gbase:go")`, then `gbase:monitor` for an open PR. Nothing ships by hand, `go` merges only with `--merge`, and it never force-pushes. Branch, commit, and PR format come from [conventions.md](conventions.md), not from `worker.md` or a playbook. |
| `/setup-pstack`, the `pstack-models` rule | Not in gbase. See Models. Never write `~/.claude/rules/` or `~/.cursor/`. |
| `make-bot-ui`, the **Worktree cleanup** playbook, the benny automation | Not in gbase. Say so in one line and continue. `skills/poteto-mode/scripts/worktree-audit.sh` is read-only and can still be run; deleting worktrees, simulators, or caches is the user's call. |

## Tools

| Cursor | Claude Code |
| --- | --- |
| `Task` | `Agent` |
| `AskQuestion` | `AskUserQuestion`. First check `printenv AGENT_HEADLESS`; when it prints `1`, follow [headless.md](headless.md) instead of asking. |
| Open a todolist, copy steps into the todolist tool | The session's task tool (`TodoWrite` or `TaskCreate`). Without one, keep the list in your reply. |
| `Grep`, `Glob` | `Bash` with `rg` when the session has neither. |

## Subagent fields

| Cursor | Claude Code |
| --- | --- |
| `subagent_type: generalPurpose` | `subagent_type: "general-purpose"` |
| `poteto-agent`, `comment-sicko` | `gbase:poteto-agent`, `gbase:comment-sicko`. Put the absolute path of `<root>/skills/poteto-mode/SKILL.md` in every prompt to either one: it is how the agent finds this file. |
| `readonly: true` | `subagent_type: "Explore"`. It keeps `Bash`, so the brief also says "do not edit files", and you check `git status` afterward. |
| `readonly: false` | `general-purpose` |
| `environment: "cloud"` | `isolation: "worktree"`. Name the branch or commit the worker checks out. |
| `environment: "local"`, `run_in_background: true` | Omit. |
| `cloud_base_branch: <b>` | Tell the worker to check out `<b>` first. |
| `resume` | Spawn a new agent and paste the earlier result into its brief. |
| `file_attachments` | List the paths in the brief. |

## Models

gbase has no per-role model rule. The session's model is already chosen: by the user, or by the slot in `.claude-plugin/factory.json` for a headless run. Treat every `pstack-models` line as missing and every Cursor slug (`claude-opus-5-5-xhigh-fast`, `gemini-4-neon-xhigh`) as unusable.

| pstack role | In gbase |
| --- | --- |
| Code, prose, judgment, verification, swarm workers | Omit `model`: the agent runs on the session's model. |
| Bulk read-only work (sweeping files, logs, transcripts) | `subagent_type: "gbase:scout"` |
| A diverse panel (`arena runners`, `interrogate reviewers`, a cross-judge) | One seat with `model` omitted and one on another Claude family (`opus` on a Sonnet session, otherwise `sonnet`). Keep at least two seats. Add a `fable` seat only when the session runs on Fable or the user named it for this task. No Gemini seat exists; say the panel ran on Claude models only. |
| A reasoning level (`high`, `xhigh`) | Pass `effort` when the `Agent` schema has it; otherwise drop it. |

A model the user names for this task overrides the table.

## Paths

| Cursor | Claude Code |
| --- | --- |
| `.cursor/skills/`, `~/.cursor/skills/` | `.claude/skills/`, `~/.claude/skills/` |
| `.cursor/rules/*.mdc`, always-applied rules | `CLAUDE.md`, or `AGENTS.md` when no `CLAUDE.md` exists |
| `https://github.com/cursor/plugins/blob/main/pstack/<path>` | `<root>/<path>` when that file exists; read the local copy. Give the user the URL when they need a link. |
| Transcripts in `~/.cursor/projects/<slug>/agent-transcripts/` | `~/.claude/projects/<slug>/<session>.jsonl`, the slug being the workspace path with each `/` and `.` changed to `-`. `<session>/subagents/` holds subagent transcripts. Read only this workspace's folder. |

## Cursor-only features

When a step needs one of these, put one line in your reply, `Claude Code에 없음: <step>. <reason>.`, and go on. Don't stop, ask, or retry.

| Cursor | In gbase |
| --- | --- |
| Cursor Automations, routines, `api2.cursor.sh` webhooks, `SendToUser` secret requests | Skip with the line. Unattended runs are started by an orchestrator through `scripts/gbase-run` ([orchestrator.md](orchestrator.md)), not from inside a skill. |
| Bugbot | Its PR comments are ordinary review threads; `gbase:monitor` triages them. Skip a step that starts or waits for Bugbot when the PR has none. |
| Cursor cloud agents | A worktree agent, as in Subagent fields. Skip a step that needs the cloud machine itself. |
| A built-in PR tool | `gbase:go`. |

## gbase rules that override a pstack skill

- **Language.** Text the user sees is Korean; code, paths, commands, and labels stay as they are.
- **Stop before irreversible steps.** Deploys (including a merge that triggers one), force-push, data deletion, store submits, and messages to people (team chat, tickets, customer mail) need the user, even where a pstack skill says "just do it" or "don't stop". Under `AGENT_HEADLESS=1` they become `결정 필요:` lines ([headless.md](headless.md)).
- **Installs.** `statechart` installs TLC and Java through `mise` on first run, its renderer wants the npm package `pele`, and `poteto-mode/scripts` runs `bun install --frozen-lockfile`. Say which install is about to run before it does; under `AGENT_HEADLESS=1` run only the lockfile- or checksum-pinned ones.
- **Risk tier.** When `gbase:go` or `gbase:review` set a tier (`low` / `medium` / `high`), a pstack skill run inside them scales its fan-out to that tier instead of its own default.
