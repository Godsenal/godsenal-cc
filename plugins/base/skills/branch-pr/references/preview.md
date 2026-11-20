# Preview before the PR

Read when `ship-prep start` prints a `preview:` line, or the user asked to see the change before the PR (`--preview` here or on `gbase:go`, "PR 올리기 전에 보여 줘"). The change is committed and drafted on this machine, shown to the user, and pushed only when they say so. Nothing reaches the remote, the PR list, or a ticket before that.

## Does it apply

**The request wins over the setting.** Words in this task that ask for the PR or the merge itself ("PR 올려 줘", "바로 올려", "통과하면 머지", `--no-preview`) open it without the stop: go on with Step 2 as written and add `--no-preview` to `ship-prep open`. A slash command alone (`/gbase:work <task>`, `/gbase:go`, `/gbase:branch-pr`), "마무리해 줘", and a `--merge` that came from the project's instructions are not that request.

Otherwise the script's line says where to start: `preview: on` (or the user's request) → Prepare. `preview: prepared` → Asking. `preview: changed` → After a change.

## Prepare

Steps 2 to 4 as written (branch, commits, compat-check, the draft and its unslop pass), all local: no `ship-prep open`, no `gh pr create`, no `ship-prep assets`, no write-back. A screenshot is `![<label>](<absolute local path>)` until the PR opens. Then:

```bash
"${CLAUDE_SKILL_DIR}/scripts/ship-prep" preview <draft>                   # what the preview needs
"${CLAUDE_SKILL_DIR}/scripts/ship-prep" preview <draft> --write <<'EOF'   # saves the text and records the commit
<the preview>
EOF
```

The first call checks the draft and prints `ship: local …`, `PR 본문 초안: …`, `preview: <file>`, the title, the commits, and each file's line counts. The second saves the text to that file, outside every repo (`~/.gbase/previews/`), and records HEAD, the draft, and the tree as what was shown. Add `--reviewed` to it when `go`'s Steps 2 to 4 ran for this commit in this session: a later `/gbase:go` then skips them. Without it (`/gbase:branch-pr` on its own) a later `go` reviews first.

## The preview

Save it with `--write` and print the same text in the reply; a link to the file is not enough. The reader is new to this codebase and will explain the PR to its reviewers, so write what they could say out loud: plain sentences, no session shorthand, and half a line of explanation the first time a term of this codebase appears. Korean, short sections and tables, no paragraph over two sentences. A claim comes from something read or run in this session, or it is marked `미확인`.

```markdown
# PR 미리보기: <PR 제목>

**한 줄 요약** <쓰는 사람이나 호출하는 코드에 무엇이 달라지나> · **티켓** <키, 없으면 없음> · **위험도** <low/medium/high> (<그렇게 본 경로나 위험>)

## 무엇을 왜 바꿨나
- 전에는 <동작> → 이제는 <동작>. <이유>

## 변경 지도
| 읽는 순서 | 파일(묶음) | 하는 일 | 줄 수 |
|---|---|---|---|

## 리뷰가 찾은 것
남긴 것 <n> · 고친 것 <n> · 반박된 것 <n>

| 남긴 것 | 어디 | 왜 남겼나 | 내가 정할 것 |
|---|---|---|---|

## 확인한 것과 확인하지 못한 것
| 무엇을 | 명령이나 방법 | 결과 |
|---|---|---|

**확인하지 못한 것** <항목마다: 왜 못 했나, 사람이 어떻게 확인하나>

## 리뷰어가 물을 만한 것
- **Q.** <질문> **A.** <답>

## 이대로 열릴 PR
| 브랜치 | 커밋 | PR 제목 | 본문 초안 |
|---|---|---|---|
```

- **무엇을 왜**: 3 to 6 lines about behavior, never a file list.
- **변경 지도**: one row per file or group (generated and repeated files share a row), in the order that makes the change easiest to follow: the entry point or type first, tests last. Line counts are the script's `files` lines.
- **리뷰가 찾은 것**: what was left goes first, because the user has to decide it: every deferred finding, and polish's `open` and `awaiting confirm` rows. Fixes get one line each, refuted findings only a count. When no review ran, say which tier or flag skipped it; that is not "nothing found".
- **확인**: every `verify:` and `behavior:` line with its command and result. A `behavior: skip`, a `differs:` input, and an unchecked done condition go under 확인하지 못한 것.
- **리뷰어가 물을 만한 것**: two to four, with answers: why not the obvious alternative, what else this touches, compatibility and deploy order. Use compat-check's verdict, and a `gbase:blast-radius` result when the session has one.
- **이대로 열릴 PR**: from the script's output, and that nothing is pushed yet.

## Asking

One `AskUserQuestion`: **PR 열기** / **초안 PR로 열기** / **여기서 멈춤** (고칠 것을 말하면 고치고 다시 보여 준다).

- **PR 열기, 초안 PR로 열기.** Upload the local screenshots now (`ship-prep assets`, then rewrite their links), run `ship-prep open <draft>` (`--draft` for the draft), and go on from Step 5 as written: the `pr:` line, the write-back, and under `go` its Step 6. No review or check runs again. If `open` refuses because the commit, the tree, or the draft is not what was shown, go to After a change. In a later session `go` no longer knows what its review left: the preview's 남긴 것 rows are the deferred findings `--merge` waits on, and Step 6 runs monitor without `--no-review`.
- **여기서 멈춤.** End with `ship: local …`, `PR 본문 초안: …`, and `preview: <file>` at column 0, and say that `/gbase:go` on this branch comes back to this question. When files were left uncommitted on purpose (`--partial`), say `/gbase:branch-pr` instead: `go` takes an uncommitted tree as the change to review.
- **A fix the user names** → After a change.

**Headless** (`AGENT_HEADLESS=1`): the stop holds. The setting means the team sees nothing before its owner has read it, and a recommendation can't do that reading. Push nothing, put the preview in the report, end with the three lines above, and add `결정 필요: <branch> @<sha> PR 열기 전 미리보기 <preview file> → 열지 않음 (추천: 미리보기를 읽고 PR 열기; 사람이 할 일: 이 브랜치에서 /gbase:go 로 PR 열기)` ([headless.md](../../../references/headless.md)). An `AGENT_ASK_CMD` answer that picks an option is applied.

## After a change

A fix the user asked for after reading, or files that changed since the preview. Redo only that part: make the fix, run the checks that cover the changed files, and where `go`'s tier calls for a finder, one review over that diff alone. Under `go` with uncommitted edits, its Steps 2 to 4 have just done this. Commit (amending is fine, nothing is pushed), update the draft where the change shows, run `ship-prep preview` again, and show the new preview with what changed since the last one on its first line.
