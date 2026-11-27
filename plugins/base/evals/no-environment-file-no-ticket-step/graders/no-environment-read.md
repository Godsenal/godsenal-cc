---
type: regex
pattern: '"(?:file_path|command|path)"\s*:\s*"(?:[^"\\]|\\.)*references/(?:explore-)?environment\.md'
match: not_contains
target: trace
arm: both
---
