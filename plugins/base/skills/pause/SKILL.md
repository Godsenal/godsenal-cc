---
name: pause
description: "Stops in-flight work cleanly so a cold-start agent can resume it — finishes or backs out of the current step, commits the tree as one wip commit whose body is the resume note (intent, progress, what's verified, next step, gotchas), and pushes nothing new. Use only when explicitly asked to pause, stop for now, hand off, or wrap up before a restart or compaction; never on 'keep going' or 'don't stop'. Resume with gbase:pickup."
allowed-tools: Bash Read Write
disable-model-invocation: true
---

# /gbase:pause

Leave a checkpoint a cold-start agent can resume from. Ported from pstack's `pause-safely` playbook (MIT). Explicit only: on "keep going", "going to bed, keep going", or "don't stop", do not pause.

## 출력 언어

사용자에게 보이는 텍스트는 **한국어**로 쓴다 — 진행 보고, 요약, 리포트 표의 설명 칸, 집계/tally 라인, `AskUserQuestion`의 질문·헤더·옵션·설명까지 전부. 하위 에이전트를 띄울 때도, 결과가 사용자에게 그대로 노출되는 텍스트는 한국어로 돌려달라고 프롬프트에 적는다.

영어 그대로 두는 것: 코드·식별자·파일 경로·명령어·스킬/툴 이름, 고정 라벨과 상태 키워드(`critical`/`high`/`medium`/`low`, `PASS`/`FAIL`, `✅`/`⚠️`), 그리고 커밋 메시지·브랜치 이름 — 이건 레포의 기존 관례(`git log`)를 따른다. PR 제목·본문은 기본 **한국어**로 쓴다 — 섹션 제목 같은 템플릿 라벨은 영어로 두고, 레포가 분명히 다른 언어로 PR을 써 왔거나(예: 영어 오픈소스) 사용자가 요청하면 그 언어를 따른다.

사용자가 다른 언어로 요청하면 그 언어를 따른다.

## Steps

1. **Stop at a safe boundary.** Finish the current atomic step or back out of it. Start nothing new; stop background agents and monitors this session started.
2. **Push nothing** — not even to a branch that's already pushed (`branch-pr` won't unwrap a pushed pause commit, so its note would land in the PR history). No PR, no merge.
3. **Make it durable in one commit.** On the default branch, first `git switch -c wip/<topic>` — a pause never commits to `main`. Then commit everything (untracked included) as one `wip: <topic>` commit — except secret-looking files (`.env*`, private keys, token dumps) that aren't gitignored: leave them out and name them in the note; use `--allow-empty` when the tree is clean so the note still lands. If the tree is broken, say so in the first body line.
4. **The commit body is the resume note**, written for an agent that has never seen this session:

```text
wip: <topic>

Intent: <what the user wants, in their terms>
Done: <what's finished, and how each piece was verified — or "unverified">
State: <branch, open PR, running processes stopped, anything half-applied>
Next: <the first concrete action on resume>
Files: <the key paths>
Gotchas: <what cost time this session, decisions already made and why>
```

The `Intent:` line is the marker `gbase:pickup`, `gbase:go`, and `gbase:branch-pr` use to recognize a pause commit — keep it. Body text follows the repo's commit language. A temp file alone isn't enough — `/tmp` doesn't survive a reboot, and `gbase:pickup` reads `git log`.

## Reply

Where you stopped, what's on disk versus only in this session, the commit (hash, branch, tree clean or not), and the first action on resume. This is a pause, not a final report.
