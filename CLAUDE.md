# CLAUDE.md

A Claude Code plugin marketplace (`godsenal`) with two plugins — `gbase` (dev workflow: review, polish, PR, monitor) and `gapp` (app-building harness: idea → App Store). No build step, no dependencies; everything is markdown skills. What each skill does lives in its own `SKILL.md` and in `README.md` — don't duplicate it here.

## Layout

```
.claude-plugin/marketplace.json     registry — one entry per plugin, with version
plugins/base/  → gbase              .claude-plugin/plugin.json, skills/<name>/SKILL.md, commands/*.md (legacy),
                                    references/ (rules several skills share), .claude-plugin/factory.json (orchestrator slots)
plugins/app/   → gapp               .claude-plugin/plugin.json, skills/<name>/SKILL.md (+ references/)
scripts/check.py                    repo checks CI runs (.github/workflows/check.yml)
```

Plugin names carry a `g` prefix (`gbase`); directories don't (`plugins/base/`).

## Conventions

- **New work goes in `skills/<name>/SKILL.md`.** `commands/` holds only the two legacy commands (`find-skills`, `branch-pr`).
- **Every change bumps the version** in both `plugins/<p>/.claude-plugin/plugin.json` and `.claude-plugin/marketplace.json` (patch for fixes/wording, minor for new or reworked skills) — installed plugins don't update otherwise. Update `README.md` when a skill's behavior or usage changes; update `plugin.json` keywords when skills are added or removed.
- **Output language.** Every skill/command carries a `## 출력 언어` block: user-facing text in Korean; PR titles and bodies in Korean by default (template headings stay English; a repo that clearly writes PRs in another language, or a user request, wins); code, paths, commands, status labels, and commit/branch names stay as the target repo's convention. gapp app artifacts (UI copy, store metadata, landing/privacy pages) follow the app language in `docs/HARNESS.md`. Keep the block when editing a skill.
- **Cross-skill contracts — change both sides together:**
  - `compat-check`'s verdict tokens (`✅ No special deploy ordering needed` / `⚠️ Requires ordered rollout`) are parsed by `branch-pr`.
  - `go` calls `gbase:review` with `pre-PR mode; defer, don't ask; … start at Stage 2`, and `gbase:monitor` with `--no-review` / `--draft`; monitor's `--draft` flip and `--merge` wait on the deferred-findings count `go` passes, and `work` ends with `go`, adding `--merge` only when the user or the project's instructions ask; `go` hands `branch-pr` its risk tier and check results as `Risk:` / `Verification:` lines, and both classify risk with the same rule (`high` / `medium` / `low`) — change them together.
  - `pause` leaves a `wip:` commit whose body is the resume note and starts with an `Intent:` line — the marker `pickup`, `go`, and `branch-pr` use to recognize it; `go` ships unpushed pause commits on a clean tree and `branch-pr` soft-resets all of them into real commits.
  - `setup` writes the `<!-- gbase:verify -->` block in the target repo's `CLAUDE.md` that `go`'s verification gate reads; `create-verify` generates `.claude/skills/verify-*` that `go` runs for touched features, and `go` also runs pstack's `.claude/skills/verify/`.
  - Orchestrator contract (`plugins/base/references/orchestrator.md`, `headless.md`, `.claude-plugin/factory.json`): no orchestrator is ever named in plugin files — only `AGENT_*` variables, files, and report lines. Headless rules live once in `headless.md`; every skill or command that can `AskUserQuestion` points at it in one line (check.py enforces). `go` passes `branch-pr` `Ship-owner: orchestrator; PR-body-file:` and both print the `ship:` / `PR 본문 초안:` lines; `monitor --until-settled` ends with a `settle:` line; `go` and `reproduce` write the evidence file format; each `factory.json` slot names a skill that exists.
  - `bug-fix` starts with `gbase:reproduce`, which only writes the failing check; the fix stays in `bug-fix`.
  - gapp stages auto-continue to the next stage and update `docs/HARNESS.md`; stage numbers (0 kickoff … 8 store-submit) must match across `kickoff`, each skill's description, and `README.md`.

## Writing skills

Follow Anthropic's skill-authoring guidance (platform.claude.com/docs/en/agents-and-tools/agent-skills/best-practices, code.claude.com/docs/en/skills). In this repo that means:

- `description`: third person, what it does + when to use it, key use case first; it's the only part always in context (listing truncates at 1,536 chars). Implementation detail belongs in the body.
- Body: only what Claude wouldn't already know — contracts with other skills, safety rules, and gotchas learned from real failures, each with a short reason. No step-by-step coaching of things the model does unprompted, no repeated rules, no long example sessions. Invoked skill bodies stay in context for the rest of the session, so every line is a recurring cost.
- Emphasis (bold, "반드시", NEVER) only on the one or two rules that actually get skipped.
- Exact commands only for fragile operations (git safety, deploy triggers); prose for judgment calls.
- Keep `SKILL.md` under 500 lines; move bulky reference material to a file linked directly from `SKILL.md` (one level deep).
- Name MCP tools fully qualified (`mcp__<server>__<tool>`).
- Side-effecting skills (push, deploy, submit) keep their own confirmation gate or `disable-model-invocation: true`.

<!-- gbase:verify:start -->
## Verify

- check: `python3 scripts/check.py --base main` — JSON validity, version sync and bump, frontmatter, line/description limits, `## 출력 언어` blocks, and the cross-skill contract tokens above. CI runs it on every PR (`.github/workflows/check.yml`); when you add a contract, add its token to `CONTRACTS` in the script.
- trigger test (manual, not run by `go`): `/plugin marketplace add ./`, `/plugin install gbase@godsenal`, then `/reload-plugins` and give Claude a task that should trigger the skill — confirm it loads the skill rather than improvising.
<!-- gbase:verify:end -->
