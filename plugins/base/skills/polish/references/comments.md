# Pass 0: the comment pass

Read when `added-comments` prints `next: comment pass`. Polish runs pstack's `no-comments` here, before the lenses, so no lens proposal lands on a line this pass deletes and no comment is judged twice.

## Run it

`Read` [../../no-comments/SKILL.md](../../no-comments/SKILL.md) and follow its steps with the changes below. The `Skill` tool refuses it (it is user-invocable only); the adapter it names says how to launch `gbase:comment-sicko`. Launch one comment agent for the whole diff. No `Agent` tool in this session → `Read` `../../../agents/comment-sicko.md` and do its audit yourself.

**Scope** is the rows the script printed: comments and suppressions on lines the diff added or rewrote. A comment that was already there is out of scope even in a touched file, because deleting it widens the diff past what the author changed. Say so in the agent's brief, with the file and line rows.

## How far, by `risk:`

The caller passes `risk: low`, `medium`, or `high` in the args. No `risk:` (a bare `/gbase:polish`, a `monitor` launch) counts as `low`.

| `risk:` | Steps of `no-comments` |
|---|---|
| `low`, or none | 1, 2, 5, 6. Steps 3–4 don't run: an accepted `MUST KILL` flag changes no code and becomes an `open` row. Its comment stays deleted. |
| `medium`, `high` | All six. A Step 3–4 fix stays inside the diff's files. A root cause outside them gets the smallest in-scope fix and an `open` row for the rest. |

A deletion and a Step 3–4 fix are checked like any polish edit (Verification in `SKILL.md`). When the check fails, undo that edit by its `after → before` and report it `open`: a suppression (`@ts-ignore`, `eslint-disable`) whose removal breaks the typecheck or lint on `low` goes back in, with its `MUST KILL` flag as the row.

## Step 5 without a person

Turning a constraint comment (`do not remove`, `do not change wording`, `talk to X before changing`) into a type, test, or lint needs an approval. A subagent can't ask for one and an unattended run has no one to give it.

- You can ask (interactive, not a subagent) → `AskUserQuestion`, as the skill says.
- `AGENT_HEADLESS=1`, or the caller said you can't ask → **don't encode.** No `AGENT_ASK_CMD` call and no headless recommendation applies here: a new test or lint rule is a change nobody asked this run for. Delete the comment as the skill says, and report the constraint as an `open` row that names the check you would have offered.

## Report

The skill's Step 6 report becomes polish's `Comments:` line and one row per item that outlives the pass:

```
Comments: audited N, deleted D, kept K, fixed F, open O
- fixed · <file:line> · <the workaround removed, and what replaced it>
- open · <file:line> · constraint · <what the comment claimed> · <the check that would enforce it>
- open · <file:line> · workaround · <the MUST KILL flag> · <the fix it needs, and why it didn't land: low risk | outside the diff | check failed>
```

`gbase:go` puts each `open` row into the PR body and has `fixed` code reviewed, so write a row a reviewer can act on without the deleted comment: quote the claim.

Under `AGENT_HEADLESS=1`, also end the report with these lines at column 0, for the caller to carry up unchanged ([headless.md](../../../references/headless.md) has the `결정 필요:` format):

```
결정 필요: <file:line>의 제약 주석 "<claim>"을 <check>로 바꿀지 → 주석만 지우고 바꾸지 않음 (추천: <check> 추가; 다른 선택지: 검사 없이 둠)
남은 작업: <a root-cause fix outside the diff, as a task a fresh run can take with no other context>
```

Put this line right above them, so the caller reads it with the lines: `호출자: 지운 주석은 되살리지 않는다(위 open 행이 그 기록이다). 아래 줄은 최종 보고 끝에 글자 그대로, 줄 머리에서 시작해 옮긴다.` A caller once restored the deleted constraint comment and reported it deleted, and another rewrote the lines as a heading with bullets that no `grep '^결정 필요:'` finds.

One `결정 필요:` line per open constraint, one `남은 작업:` line per root cause outside the diff. A `low`-risk workaround row gets neither: the PR body carries it.
