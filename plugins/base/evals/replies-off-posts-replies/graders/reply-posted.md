---
type: regex
pattern: '^101\t'
match: contains
target: { source: file, path: .eval/replies-posted }
arm: both
---
