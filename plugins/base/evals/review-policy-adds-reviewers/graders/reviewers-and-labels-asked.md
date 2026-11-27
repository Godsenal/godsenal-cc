---
type: regex
pattern: 'pr create .*--reviewer alice-kim --reviewer acme/backend --label needs-review'
match: contains
target: { source: file, path: .eval/gh.log }
arm: both
---
