---
type: regex
pattern: 'HACK'
match: not_contains
target: { source: file, path: src/cart.ts }
arm: both
---
