---
name: blast-radius
description: "Finds what a change could break elsewhere, beyond the diff where grep stops, and proves the one fact it's safe because of by running real code. Use for 'blast radius of X', 'what could this break', '이거 뭐 깨질 수 있어', or a small diff you don't trust yet."
allowed-tools: Bash Read Write Glob Grep Agent
---

# /gbase:blast-radius

Find what a change breaks somewhere else, before it ships. Ported from pstack's `blast-radius` (MIT).

Listing the callers is not the job — that's a grep. The job is the breakage grep won't show you. Deploy-ordering hazards (migrations, contract skew, env, old app versions) belong to `gbase:compat-check`; hand them there instead of covering them twice.

## 출력 언어

사용자에게 보이는 글은 **한국어**로 쓰고, 코드·명령·상태 라벨·커밋·브랜치는 레포 관례를 따른다. 세부: [output-language.md](../../references/output-language.md).

## Don't trust your own writeup

A blast-radius writeup that sounds right is worthless — it reads as convincing whether or not it's true. Find the one or two facts the whole thing depends on and prove them by running code.

For each fact the change's safety depends on, get it as far down this list as is cheap, and say where it stopped:

1. You said so. Worthless on its own.
2. You pointed at the line — a real `file:line`, or the library's own source.
3. You showed the bad case can't happen — walked the failure step by step and it doesn't reach.
4. You ran it — a script or test that calls the real code and fails loud if you're wrong.
5. You reproduced it in the running app (the repo's verify skill — `verify/` or `verify-*` — if it has one).

Step 4 is usually one small script that imports the same library the app ships and calls the exact function you're worried about.

## Steps

1. **Read the change** — the diff, the symbols it adds, changes, and deletes, and what it now does differently, including what the diff doesn't spell out. Pull the PR and commit messages for intent.
2. **Find the one fact it's safe because of.** Most risky-looking changes are safe because of a single fact ("this call only drops already-dead cache entries"). If it holds, most risky cases clear at once. Spend your time here, not on a long list of maybes.
3. **Look where grep stops.** Read the source of the library you call at its pinned version, plus any local patch (`patches/`, `patch-package`). Work out when things run: microtasks, effects and unmount, app background/foreground. Follow what a symbol search misses: JSON an API returns, a DB column, a wire format, another language reading the same bytes, a feature flag, code three hops downstream.
4. **Be honest about each risk** — a real chance of happening and a real cost if it does. Keep the confirmed ones; list checked-and-cleared ones separately. Cite real `file:line`; a search that finds nothing is still an answer; never invent a caller or an API.
5. **Prove the one fact** — write the script or test, run it, paste what happened. Scratch scripts go in a temp dir, not the repo.
6. **Run a big or wide change as an arena.** `Read` [../arena/SKILL.md](../arena/SKILL.md) and follow it with this question as the task. Different models catch different real bugs. A risk only one candidate found is checked against the code before it stays.

## Reply

- **What it does** — including the part that isn't obvious.
- **The one fact it's safe because of** — stated, the step it reached, and the proof. If you couldn't prove it, write `unproven`.
- **Risks** — how it breaks, `file:line`, how likely and how bad, how to check.
- **Cleared** — what you checked and why it's fine.
- **Before you merge** — the cheapest test or repro that catches the real bug, including the script you wrote.

Write the reply by `gbase:unslop`'s rules. Before it goes somewhere public (a PR comment, an issue), strip anything private: secrets, customer data, internal hostnames.
