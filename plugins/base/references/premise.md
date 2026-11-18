# The same check still fails after two fixes

Read when two fixes for one check have each left it failing: `go`'s verification gate after its second fix attempt, monitor's `ci` line after the second fix it pushed for that check. Fixes that fail the same gate share a premise, and a third one written on it fails the same way. This is pstack's [attack-the-premise](../skills/principle-attack-the-premise/SKILL.md), placed before the stop that both skills already had: a stop that hands over only "failed twice" leaves the person to redo the diagnosis.

Before stopping, and before any third fix:

1. **Write the premise**: the one sentence both fixes assumed ("the test fails because the mock returns the old shape").
2. **Make one observation that would come out differently if the premise were false**, and run it: print the value at the assertion, run the one failing case alone, run it on the base commit, check which commit the failing CI run built. Reading the code again is not an observation. One is enough; this is not an investigation.
3. **Then stop and ask**, with the premise, the command and what it showed, and whether the premise held. Options: fix now on the corrected premise / leave the failure as it is (`go`: open the PR anyway) / abort. There is no third fix before the answer, even when the observation overturned the premise: the next fix is the person's call now that two have missed.

## Headless

Nothing is asked ([headless.md](headless.md)), and no third fix is made: `go` opens the PR with the failure in Evidence, monitor leaves the check red for its `settle:` line. The `결정 필요:` line carries the premise and the observation in its question part. Keep ` → ` out of `<적용한 것>`: the caller splits the line on the last one.

```
결정 필요: <체크>가 수정 두 번 뒤에도 실패. 전제 "<한 문장>", 관찰 `<명령>`: <본 것> (전제 <유지|반박>) → <적용한 것> (추천: <추천한 것>; 다른 선택지: <a> / <b>)
```
