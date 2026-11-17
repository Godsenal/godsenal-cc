# A correction becomes a check

Read when the task corrects a mistake an agent made: the user says it happened again, or hands over `교훈:` lines.

Fix it, then give it the cheapest catch that holds, trying these in order:

1. code that makes the mistake impossible (the type, the API shape, the default)
2. a lint rule, a type, or a test that fails on it
3. a journey in the repo's verify skill that an agent drives on the real app
4. a written rule (a skill line, `REVIEW.md`), only for a judgment call none of the above can check

Name the level you landed on and why a higher one didn't fit. `gbase:correct` does this for a whole class of mistakes; across 453 runs it never ran on its own, so a correction handled in `work` otherwise ends as one more line of text.
