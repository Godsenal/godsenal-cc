---
type: regex
pattern: 'ship: local \S+ @[0-9a-f]{7} — \d+ commits, not pushed'
match: contains
target: trace
arm: both
---
