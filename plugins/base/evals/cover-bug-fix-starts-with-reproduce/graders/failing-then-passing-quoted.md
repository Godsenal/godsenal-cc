---
type: llm
arm: both
---
The final report quotes the output of a check that failed before the fix, showing the wrong value `2h 30m` where `1h 30m` was expected (an assertion diff or the printed value), and the output of the same check passing after the fix. A report that only says the check failed or passed, without the output, does not pass.
