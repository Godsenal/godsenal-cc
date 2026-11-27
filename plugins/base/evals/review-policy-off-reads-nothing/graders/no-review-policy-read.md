---
type: regex
pattern: '"(?:file_path|command|path)"\s*:\s*"(?:[^"\\]|\\.)*review-policy\.md'
match: not_contains
target: trace
arm: both
---
