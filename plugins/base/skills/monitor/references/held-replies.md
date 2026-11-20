# Held replies

Read when `pr-status` prints a `replies: draft` line, before handling any comment. The user posts under their own name here, because their environment file's `## Shipping` says `review replies: draft` ([environment.md](../../../references/environment.md)), or this run was asked not to reply (`--hold-replies`, "답글은 달지 마"). A reviewer reads a reply as the author's own words, and a push that follows their comment as the author's answer.

## What changes

- **Nothing is posted on the PR.** No thread reply, no PR comment, no `CHANGES_REQUESTED` summary, and no note [merge.md](merge.md) would leave (tell the user `CI 미실행 …` instead).
- **A fix made for a comment is committed and not pushed**, whether a person or a bot wrote the comment. One commit per fix, as always.
- **`conflict` and `ci` are handled first and pushed as usual.** They answer no one, and the script lists them ahead of `comments` here. Once a comment's fix is committed, a later fix can't be pushed past it. Commit it on top and say it waits with the others.
- Classification, the trust rule, polish, and the convergence rules of [comments.md](comments.md) stay. `gh pr ready` and `gh pr merge` stay with merge.md, which runs only on `next: settled` or `merge: gate passed`. Neither prints while a comment is open or held.

## Draft

Write each reply as the user would post it themselves, in the language of the thread and the PR body (a language the environment file's `## Conventions` names wins). No tag that says draft or AI, and no "the maintainer". comments.md's two lines that speak of one are not used here. The wording below is the English form; in a Korean thread the first row is `<short-sha>에서 반영했습니다.`, and so on for the rest.

| Outcome | `verdict` | Reply |
|---|---|---|
| Applied | `fixed`, with `commit` | `Addressed in <short-sha>.` |
| Not applying it | `declined`, with `why` | `Keeping the current approach: <reason>.` |
| A question | `answered` | the answer |
| Out of scope | `out-of-scope` | `Out of scope for this PR — tracking separately.` |
| The user decides first | `undecided` | none yet |

- `why` is the reason and the `file:line` that shows it, enough for the user to explain the decline to the reviewer in person.
- `undecided` is a comment comments.md says to ask about. Ask as it says, and the answer makes it `fixed` or `declined`. Headless, it stays `undecided` with the options in `why`.

Record every comment of this sweep in one call:

```bash
"${CLAUDE_SKILL_DIR}/scripts/pr-status" drafted <<'EOF'
{"id": <the number in [thread <id>]>, "verdict": "fixed", "commit": "<sha>", "reply": "Addressed in <short-sha>.", "gist": "<the comment in one line, in Korean>"}
{"id": <id>, "verdict": "declined", "reply": "…", "why": "<reason> — <file:line>", "gist": "…"}
EOF
```

It prints the table (`댓글 | 판단 | 수정 커밋 | 답글 초안`) and a `reply drafts: <path>` line, the same table as a file outside the repo. From then on the script lists those comments under `held replies`, not as open, in a later watch and in another worktree too. A held comment is never fixed or drafted again; one left `undecided` by a headless run is asked about once a person is there. A fix whose commit a rebase or an amend rewrote is marked `rewritten`: record that comment again with the new sha, so the reply cites a commit the PR has. It is open again when someone adds a comment to it (`new comment since a draft`: read the thread, keep the earlier fix), and it leaves the list when the user replies or resolves it. A finding from a `note` has no id to record, so hold its fix with the rest and name it beside the table.

## Ask

Show the table as printed, then one `AskUserQuestion`:

- **푸시하고 답글도 올리기** → push, then post each draft exactly as shown, by comments.md's Reply commands.
- **푸시만 하고 답글은 내가 쓰기** → push. Nothing is posted and the comments stay held.
- **멈춤** → nothing is pushed. What the user asks to change goes into a new commit, is recorded with `drafted` again, and is shown again.

With no commit in the table the first two are "답글 올리기" and "내가 쓰기". The answer covers this table only. The next round of comments is drafted and asked again. A later request to post them ("답글 올려 줘", `--post-replies`) makes the script print `next: post` and each held reply in full on a `reply:` line.

## Headless

Under `AGENT_HEADLESS=1` nothing is asked, and nothing is posted or pushed on a recommendation. For the commits a comment produced, follow the local-commit rules of [settle.md](settle.md)'s `AGENT_SHIP_OWNER=orchestrator` section, whoever owns the remote: never pushed, and `wait --handled`. Before the `settle:` line the report carries, each at column 0:

- the table as printed;
- `ship: local <branch> @<short-sha> — <n> commits, not pushed`, when a comment's fix was committed;
- the `reply drafts: <path>` line;
- `결정 필요: PR #<n> 답글 초안 <k>건과 수정 커밋 <m>개(<branch>, 푸시 안 함)를 올릴지 → 올리지 않음 (추천: <path>의 초안을 읽고 직접 답글; 사람이 할 일: 초안 확인 후 git push와 답글 작성, 또는 /gbase:monitor --post-replies)`.

The `settle:` line is the script's `사람 필요 … (답글 초안)`, because a person still has to answer.
