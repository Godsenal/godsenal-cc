# Tests the change adds or edits

Read before Stage 2 when the target adds or changes a test (a file the repo's test runner collects: `*.test.*`, `*_test.*`, `test_*.py`, `__tests__/`, `spec/`), including when the caller started you at Stage 2. The finder reads tests for bugs in them, not for whether they test anything, so this question is asked here. It is pstack's [test-behavior-not-implementation](../../principle-test-behavior-not-implementation/SKILL.md).

You read the tests yourself: no agent is launched for this. For each test the diff added or changed, with the code under test open, imagine two edits:

- **Break the behavior** (a wrong value, a skipped or doubled effect). Does the test fail? It doesn't when the assertion is loose, when the expected value is computed by the code under test or copied from its formula, or when it asserts data the test built itself.
- **Change the internals and keep every observable result** (rename a private helper, reorder internal calls, swap the algorithm). Does the test still pass? It doesn't when it asserts a call to an internal helper, a call order, or an intermediate value. What an external service receives is behavior, not internals.

A test that survives both is fine: say nothing about it. One that fails either becomes a candidate with the edit that shows it as its failure scenario:

- passes with the behavior broken → `medium`: "`<test>` still passes if `<behavior edit>`" (the suite reports coverage it doesn't have)
- fails on an internal-only edit → `low`: "`<test>` fails if `<internal edit>`, with `<observable result>` unchanged"

These candidates join the finder's in Stage 2. When a skeptic is launched for the others, it takes these too, with this added to its brief, since the usual one looks for a guard or a missing caller and would call a test candidate refuted for lack of either:

> For a candidate about a test, the claim is the edit, not a product defect. Refute "still passes if `<behavior edit>`" by showing the assertion that fails under that edit. Refute "fails if `<internal edit>`" by showing an observable result the edit changes, or that the asserted call is to an external service. If you can't, concede.

With no other candidate, no skeptic is launched for these alone: the row stands on the edit it names. A survivor is never auto-fixed (Stage 3 adds or removes no test): its action is `needs decision`, and the row names the rewrite, the public call with a concrete input and the expected value taken from the requirement. Under `go` it is a deferred finding like any other.

Leave alone tests the diff didn't touch, and snapshot or generated fixtures.
