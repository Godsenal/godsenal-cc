---
name: pickup
description: "Resumes or takes over in-flight work (a gbase:pause commit, an earlier transcript, another agent's branch, an open PR) from its trail, checking inherited claims first. Use for 'pick up where we left off', 'take over this branch', or 'what was I doing'."
allowed-tools: Bash Read Glob Grep Agent
---

# /gbase:pickup

Read the prior trail; don't redo it. Ported from pstack's `session-pickup` playbook (MIT). The complement to `gbase:pause`.

## 출력 언어

사용자에게 보이는 글은 **한국어**로 쓰고, 코드·명령·상태 라벨·커밋·브랜치는 레포 관례를 따른다. 세부: [output-language.md](../../references/output-language.md).

## Steps

1. **Locate the trail**, newest first: a pause commit (`git log --all --grep='^wip:' -5`, with an `Intent:` body line — that body is the resume note), the branch and its PR (`gh pr view`), and this project's Claude Code transcripts in `~/.claude/projects/<dir>/*.jsonl` (`ls -t`), where `<dir>` is the cwd with every non-alphanumeric character replaced by `-` (`/Users/me/my_app.v2` → `-Users-me-my-app-v2`). Read only this project's directory — globbing every project reads unrelated private sessions. Branches other agents pushed (e.g. `cursor/*`) count too. Read the last messages first, then scan back for decision points; parse a long transcript in a sub-agent (`model: "sonnet"`) and keep only the reduced timeline here.
2. **Reconstruct operational state** — branch, what landed (`git log`, `git diff` against the base), open todos, decisions made. The trail is authoritative input; resist re-deriving it.
3. **Diff done vs. pending** and name the resume point. Don't re-run the prior repro or redo finished work — a "verify from scratch" pass treats the trail as untrustworthy when it's authoritative.
4. **Verify inherited claims against the real artifact** before building on them — a passing self-report in the trail isn't proof. Check the one or two claims the next step depends on, not everything.
5. **Continue** — when `gbase:work` called you, return to it at its route step, which ships. Otherwise continue with the skill the remaining work fits (`gbase:bug-fix`, `gbase:go`, …). If the trail ended on pause commits, leave them — `gbase:go` ships them and `gbase:branch-pr` regroups them into real commits.

## Reply

Where the prior work stopped, what you inherited versus redid (ideally nothing redone), the resume point, and which claims you re-verified.
