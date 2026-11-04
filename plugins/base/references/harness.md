# Harness recipes

Text for bot skills that live outside this repo (`detached-claude-run`, `shared-browser-space-gate`). A bot copies it into its own skill; a change starts here, so the next copy picks it up. The runner contract itself is [orchestrator.md](orchestrator.md#runner).

## Starting a Claude run (`detached-claude-run`)

Default, for any task:

```bash
gbase-run start --slot task --dir <folder> --task-file <file> --account <name>
```

Code changes use `--repo <path> --slot work` instead of `--dir … --slot task`. The runner gives the run a stream-json log, `result.json`, `status`/`stop`, account fallback, the headless paragraph below, and the notify command (`GBASE_NOTIFY_CMD`), so the bot writes none of these itself. Most repeated work in the 2026-11-04 retro was a bot starting Claude directly, without them.

A direct template that still runs `claude -p` keeps to these:

- The binary is `~/.claude/local/claude`, written out. Don't look for it (`which claude`, a `PATH` guess).
- `--output-format stream-json --verbose`, and `--disallowedTools ScheduleWakeup,CronCreate` ([headless.md](headless.md#end-when-the-work-ends)).
- The run directory is `~/.claude-runs/<run-id>/`. `.done` is written after claude exits and holds exactly one line, `EXIT=<n>`, nothing else; `.ACCOUNT` holds only the account name (`default`, `c5`).
- `AGENT_HEADLESS=1` and `GBASE_RUN_ID=<run-id>` (the run directory's name) in the environment, and the paragraph below appended to the prompt. The session names its ego task spaces with that id.

## Headless paragraph for task prompts

A bare task loads no skill, so [headless.md](headless.md) reaches it only through the prompt. `gbase-run` appends this (`TASK_HEADLESS` in `scripts/gbase-run`); a direct template appends the same text:

> 사람이 붙어 있지 않은 실행이다(AGENT_HEADLESS=1). 묻지 말고 되돌릴 수 있는 쪽으로 진행하고, 사람이 정할 것은 최종 보고 끝에 줄마다 `결정 필요: [질문] → [적용한 것] (추천: [추천]; 다른 선택지: [a] / [b])`로 적는다. 다음은 추천이나 추정으로 하지 않고 `결정 필요: [단계] → 하지 않음 (추천: [추천]; 사람이 할 일: [할 일])`로 남긴다: 머지, 배포, force-push, 데이터 삭제, 게시·스토어 제출, 결제, 사람에게 메시지 보내기, 시크릿 커밋, 그리고 약관·법적 동의, 대표자·본인 확인 체크, 사실 진술 체크박스 중 근거가 없는 것. 규칙 전문: (gbase checkout)/plugins/base/references/headless.md

## Shared ego space gate (`shared-browser-space-gate`)

Before a run opens an ego task space, the gate checks the spaces already open, in this order:

1. **Run id in the name.** Spaces follow [ego-profile](../skills/ego-profile/SKILL.md#space-수명-헤드리스-런)'s naming, `<run-id> <작업>`. Look the run up: `gbase-run status <run-id>` (`running` is alive), or for a direct run, `~/.claude-runs/<run-id>/.done` exists or the process is gone.
2. **A finished run's space is not a conflict.** Don't wait on it, and don't close it: a payment or confirmation screen may be waiting for the person. List it in the bot's report.
3. **A space handed to the person (`agentDelegatedToUser`)** stays on the wait list only until a timeout, then drops off it, still not closed. The timeout is a person's call; until one is set, use 2 hours.
4. **No run id in the name** (a space from before this rule, or a person's own): a conflict, as before.
