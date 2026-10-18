---
name: pickup
description: "Resumes or takes over in-flight work — from a gbase:pause wip commit, a prior Claude Code session's transcript, another agent's pushed branch, or an open PR — by reading the trail as authoritative instead of redoing it, naming the resume point, and verifying inherited claims on the real artifact before continuing. Use for 'pick up where we left off', 'continue the work on X', 'take over this branch', or 'what was I doing'."
allowed-tools: Bash Read Glob Grep Agent
---

# /gbase:pickup

Read the prior trail; don't redo it. Ported from pstack's `session-pickup` playbook (MIT). The complement to `gbase:pause`.

## 출력 언어

사용자에게 보이는 텍스트는 **한국어**로 쓴다 — 진행 보고, 요약, 리포트 표의 설명 칸, 집계/tally 라인, `AskUserQuestion`의 질문·헤더·옵션·설명까지 전부. 하위 에이전트를 띄울 때도, 결과가 사용자에게 그대로 노출되는 텍스트는 한국어로 돌려달라고 프롬프트에 적는다.

영어 그대로 두는 것: 코드·식별자·파일 경로·명령어·스킬/툴 이름, 고정 라벨과 상태 키워드(`critical`/`high`/`medium`/`low`, `PASS`/`FAIL`, `✅`/`⚠️`), 그리고 커밋 메시지·브랜치 이름 — 이건 레포의 기존 관례(`git log`)를 따른다. PR 제목·본문은 기본 **한국어**로 쓴다 — 섹션 제목 같은 템플릿 라벨은 영어로 두고, 레포가 분명히 다른 언어로 PR을 써 왔거나(예: 영어 오픈소스) 사용자가 요청하면 그 언어를 따른다.

사용자가 다른 언어로 요청하면 그 언어를 따른다.

## Steps

1. **Locate the trail**, newest first: a pause commit (`git log --all --grep='^wip:' -5`, with an `Intent:` body line — that body is the resume note), the branch and its PR (`gh pr view`), and this project's Claude Code transcripts in `~/.claude/projects/<dir>/*.jsonl` (`ls -t`), where `<dir>` is the cwd with every non-alphanumeric character replaced by `-` (`/Users/me/my_app.v2` → `-Users-me-my-app-v2`). Read only this project's directory — globbing every project reads unrelated private sessions. Branches other agents pushed (e.g. `cursor/*`) count too. Read the last messages first, then scan back for decision points; parse a long transcript in a sub-agent (`model: "sonnet"`) and keep only the reduced timeline here.
2. **Reconstruct operational state** — branch, what landed (`git log`, `git diff` against the base), open todos, decisions made. The trail is authoritative input; resist re-deriving it.
3. **Diff done vs. pending** and name the resume point. Don't re-run the prior repro or redo finished work — a "verify from scratch" pass treats the trail as untrustworthy when it's authoritative.
4. **Verify inherited claims against the real artifact** before building on them — a passing self-report in the trail isn't proof. Check the one or two claims the next step depends on, not everything.
5. **Continue** with the skill the remaining work fits (`gbase:bug-fix`, `gbase:go`, …). If the trail ended on pause commits, leave them — `gbase:go` ships them and `gbase:branch-pr` regroups them into real commits.

## Reply

Where the prior work stopped, what you inherited versus redid (ideally nothing redone), the resume point, and which claims you re-verified.
