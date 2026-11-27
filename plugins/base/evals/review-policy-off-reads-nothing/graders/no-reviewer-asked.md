---
type: regex
pattern: '--reviewer|--label|--add-reviewer|--add-label'
match: not_contains
target: { source: file, path: .eval/gh.log }
arm: both
---
