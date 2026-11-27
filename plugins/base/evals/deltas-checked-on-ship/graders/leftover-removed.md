---
type: regex
pattern: 'const unused'
match: not_contains
target: { source: file, path: src/stock.ts }
arm: both
---
