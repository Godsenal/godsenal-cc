---
type: llm
arm: both
---
The final report says that a test in `src/price.test.ts` is tied to the implementation instead of the behavior: its assertions on calls to internal methods (`applyDiscount`, `roundWon`: which one is called, with what arguments, or how many times) would fail if the internals changed while `bulkPrice` still returned the same values. Naming the file without saying this does not pass.
