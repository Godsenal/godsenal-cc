# High and critical findings: mark the ones a run proved

Read at Stage 2 when a finding is rated high or critical. Reading the code says a failure is possible; a run says it happens.
One of the three skeptics takes the run angle, so no agent is added. Its prompt gets this after the usual refutation brief:

> Before you judge by reading, try once to make the failure happen: a failing test, a repro script, or a command whose output shows the wrong behavior, run against the real code. Keep everything you write in a scratch folder outside the repo and edit no product file. Report the exact command and the output line that shows the failure, or say why you could not run it (needs a device, production data, a paid call, more than a few minutes). Not being able to run it is not a refutation: judge the finding by reading, as the other skeptics do.

Then, in the report's `finding` cell, after the finding:

- The run showed the failure → `실행으로 확인됨: <command> → <output line>`. It counts as that skeptic's concession.
- No run was possible → `실행 증거 없음 — <why>`. The finding stays: the panel's majority decides it, as before. This differs from `interrogate`, which drops what no run proved; here Stage 2 has already filtered, and dropping an unproven high finding loses a real bug to a missing simulator.
- The run completed and the failure did not happen → that is the skeptic's refutation, with the command and output as its reason. One run is one vote, not the verdict.

Quote one line of output, and write every `|` in it or in the command as `\|` (`git diff \| git patch-id`): `gbase-run` splits the table on an unescaped one. The mark never changes the severity or the `action` column, and low and medium findings get no run.
