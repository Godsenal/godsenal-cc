---
type: regex
pattern: '"(?:file_path|command|path)"\s*:\s*"(?:[^"\\]|\\.)*held-replies'
match: not_contains
target: trace
arm: both
---
