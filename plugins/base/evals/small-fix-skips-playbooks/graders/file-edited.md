---
type: regex
pattern: 'Content-Type'
flags: i
match: contains
target: { source: file, path: src/screens/Settings.tsx }
arm: both
---
