---
name: plan
description: "Turns an idea or a vague request into a plan a work run can build without guessing: checks the premise, settles the decisions only the user can make (asked in rounds with a recommended answer each, so one 'ㄱㄱ' accepts them), looks facts up itself, and ends with PR-sized slices that each carry their own check. Read-only: writes one plan file, no code. Use when the user says 기획, 계획 세워, 설계해 줘, plan this, grill me, or brings an idea, a feature with open product choices, or a task too big for one PR; also on /gbase:plan <idea>. Not for a task that already names the change and how to check it: that goes to gbase:work."
allowed-tools: Read Glob Grep Bash Write Agent AskUserQuestion Skill
---

# /gbase:plan

Decide before building. The output is a plan file whose slices can each be handed to `gbase:work` as they are. The interview is modeled on Matt Pocock's `grilling` (a design tree asked frontier by frontier) and the decision classes on gstack's `autoplan`; unlike both, it runs with or without a person and its slices are sized and checked the way this harness ships.

## 출력 언어


사용자에게 보이는 텍스트는 전부 **한국어**로 쓴다 — 보고·요약·표의 설명 칸·질문과 옵션, 하위 에이전트가 돌려주는 글 중 사용자에게 그대로 노출되는 것까지. 코드·경로·명령어·스킬/툴 이름·상태 라벨(`high`, `PASS`, `✅`)은 그대로 두고, 커밋 메시지·브랜치 이름은 레포 관례(`git log`)를 따른다. PR 제목·본문은 기본 한국어(섹션 제목은 영어) — 레포가 분명히 다른 언어로 PR을 써 왔으면 그 언어. 사용자가 다른 언어로 요청하면 그 언어를 따른다.

## Headless

Before any `AskUserQuestion`, check `printenv AGENT_HEADLESS`; when it prints `1`, follow [headless.md](../../references/headless.md) instead of asking, and use the headless column of the table in step 3.

## Rules

- **No code, no commits.** The only file written is the plan. A prototype that would settle a question is named as a slice (`gbase:mockup` for a screen, the Prototype route of `gbase:work` otherwise), not built here.
- **Facts are yours, decisions are the user's.** Never ask what you can look up: what the code does, what exists already, what a library supports, what the store or API allows. Send `subagent_type: "gbase:scout"` for anything that takes more than a few reads, and keep asking the questions that don't depend on it.
- **Quote the request.** The plan opens with the user's words verbatim. Everything else is marked as decided by the user, decided here, or assumed.

## 1. Premise

Read the request and the area of the repo it touches (`gbase:how` when the area is unfamiliar). Then answer, in the plan, with evidence:

1. What is the user trying to get, in one sentence, and who notices when it works?
2. What already exists that does part of it? Name files. Reuse beats new code.
3. What happens if nothing is built? A real cost, or a guess?
4. Is there a smaller thing that gets most of it?

If the answers say the request as stated is the wrong thing to build (it exists, it can't work, a tenth of it gets the result), that is a **direction change**: step 3 says what to do with it.

## 2. Design tree

List every decision the work needs before it can be built, and what each depends on: scope (what is in, what is explicitly out), behavior at the edges (empty, error, offline, first run, existing data), data shape and where it lives, what the user sees and where, how it reaches users (migration, flag, store review, deploy order), and how you will know it works. The **frontier** is the set of decisions whose prerequisites are settled.

## 3. Settle the frontier, round by round

Classify each frontier decision, then act:

| class | what it is | with a person | headless |
|---|---|---|---|
| mechanical | one clearly right answer given the repo and the request | decide, list it | decide, list it |
| taste | reasonable people would differ: a product choice, a tradeoff, a default | ask, with your recommendation | apply the recommendation, add a `결정 필요:` line |
| direction change | you recommend something other than what was asked | ask, alone, before anything else | keep the user's direction, add a `결정 필요:` line with your case |

Asking: one `AskUserQuestion` call per round carries the whole frontier of taste decisions (up to its limit; the rest wait a round). Put your recommended option first, say in its description what it costs and what the other option would cost, and word it so accepting every first option is a complete answer. This user answers in a word; never ask for prose, and never ask the same thing twice. A round's answers move the frontier: recompute it and ask the next round. Three rounds is normal; more than five means the request is several plans, so split it and plan the first.

Stop when the frontier is empty: nothing left silently assumed. An assumption you couldn't check and didn't ask about is written as `가정:` with what would falsify it.

## 4. Slices

Cut the work into slices, each one PR:

- **Vertical.** A slice goes through every layer it needs and can be shown or checked on its own. A slice that is only "the schema" or only "the UI" is wrong unless nothing else can land first. Tests for a slice are part of that slice, not a slice of their own.
- **Sized for one work run.** In this harness a normal run is under 100 turns; a slice you expect to pass 150 is two slices.
- **Its own check.** Each slice names how its result is verified on the surface the user touches: a command and the output to expect, a screen and what it shows. "Tests pass" is not a check.
- **Order.** Each slice lists the slices it is blocked by. What others depend on goes first; a mechanical change that touches everything (a rename, a retyped field) is expand, migrate in batches, contract.
- **Self-contained.** A slice's text is the whole task for a fresh run that has read nothing else: the user's decision that applies, the files to start from, what is out of scope, the check.

## 5. Write the plan and report

Write `${GBASE_HOME:-$HOME/.gbase}/plans/<repo>-<slug>.md`:

```
# <title>
> <the request, verbatim>
## Premise        (the four answers, with files)
## Decisions      (table: decision | answer | by: user / plan / 가정 | why)
## Out of scope
## Slices         (numbered; each: task text, blocked by, check)
## Open           (what only the user can still settle; empty when none)
```

Then report, in this order: the plan path as `plan: <absolute path>` at column 0; the decisions the user made and the ones made here, in a short table; each slice as its own `남은 작업: <the slice's full task text>` line at column 0, in order (a caller starts them as work runs); and any `결정 필요:` lines last. Start nothing. With a person present, ask once whether to start slice 1 with `gbase:work`.
