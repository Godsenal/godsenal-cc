---
name: bug-fix
description: "Fixes a bug at its root cause, not where it surfaced: reproduces it first (gbase:reproduce), rules out hypotheses with runtime evidence, fixes every instance of the pattern, keeps every output and default the issue didn't ask to change as it was, and verifies on the surface it failed on. Use when asked to fix a bug or a crash, when a test or CI fails for a reason that isn't mechanical, or when something 'randomly' breaks or is flaky ('버그 고쳐 줘', '가끔 앱이 죽어', '테스트가 이유 없이 실패해'). Asked only why it broke, it stops at the diagnosis."
allowed-tools: Bash Read Edit Write Glob Grep AskUserQuestion Agent Skill
---

# /gbase:bug-fix

Fix the fault, not the place it became visible. The symptom is where a wrong state showed up; the root cause is the first place the system did something it shouldn't, or failed to handle a state it should. Ported from pstack's `principle-fix-root-causes` and `bug-fix` playbook, with `tdd` and `principle-attack-the-premise` folded in (MIT).

## 출력 언어

사용자에게 보이는 글은 **한국어**로 쓰고, 코드·명령·상태 라벨·커밋·브랜치는 레포 관례를 따른다. 세부: [output-language.md](../../references/output-language.md).

## Headless

Before any `AskUserQuestion`, check `printenv AGENT_HEADLESS`; when it prints `1`, follow [headless.md](../../references/headless.md) instead of asking.

## Every shipped line traces to runtime evidence

A change that "might help" is a hypothesis, not a fix — it doesn't ship. When evidence refutes a hypothesis, revert what it motivated. The smallest change the evidence justifies ships, nothing more.

## Steps

1. **Reproduce through `gbase:reproduce`, before the first edit**, even when the bug looks obvious and a one-line `node -e` would show it: `Skill(skill: "gbase:reproduce", args: "<the bug>")`. Its report (the command, the failing lines quoted, the expected result, the input) is what step 5 re-runs and what the evidence file and the PR's Evidence carry; three eval runs that reproduced inline fixed the bug but left none of it. If it won't reproduce, tighten conditions or instrument until it fires; ask the user only with a specific reason the surface can't be reached.
2. **Narrow the cause** by ruling hypotheses out with runtime evidence (the actual error, the actual state), until the answer is a wrong decision in the code, not a consequence of an earlier one. If the user only asked *why* it broke, stop here and report the diagnosis — don't change code unasked.
3. **Is the triggering state legitimate?** If the system may be in that state, the code that broke on it is the root cause, and handling the state there is the fix. If the state should never exist, a check where it broke hides the bug — find what produced it. Guards, retries, swallowed errors, clamped values, raised timeouts, and discarded state are the usual ways to hide one.
4. **Fix the pattern**, not the instance: find every place with the same fault and fix them together. Every output, format, and default the report didn't ask to change stays as it was: two SWE-bench runs failed the hidden test by restyling or extending output the issue never mentioned. A workaround that needs a paragraph-long comment means the code is wrong.
5. **Verify on the same surface.** The original reproduction now passes; inconclusive or a different surface is not a pass. Unit tests show branch behavior, not that the bug is gone.
6. **Add the always-on signal** if the deciding fact took a deep dig — the cheap check or log line that would have shown it at first look.

**Two failed fixes on one premise → stop.** Write the premise down as one sentence and test it directly before a third fix; the failures are evidence against it.

## Regression test

The step 1 reproduction is the regression check: when it's a test, it ships with the fix. `reproduce` writes a test only on a cheap local test path; when one would need broad harness setup, brittle mocks, timing, or production-only state, its script or request stands in — prefer no test over a bad one.

Show the failing-then-passing run in the PR's Evidence. Don't split it into a separate red commit: pre-commit hooks that run tests reject it, per-commit CI and `git bisect` trip on it, and a squash merge erases the order anyway.

## Reply

Include why the triggering state was or wasn't legitimate, and paste the failing-then-passing output verbatim. Suggest `/gbase:go` to ship — don't run it; pushing is the user's call. Under `gbase:work`, return to it instead; its Ship step ships.
