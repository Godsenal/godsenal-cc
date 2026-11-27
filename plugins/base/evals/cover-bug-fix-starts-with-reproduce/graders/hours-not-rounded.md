---
type: regex
pattern: 'Math\.round'
match: not_contains
target: { source: file, path: src/duration.mjs }
arm: both
---
