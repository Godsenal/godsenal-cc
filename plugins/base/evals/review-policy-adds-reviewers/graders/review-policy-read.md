---
type: regex
pattern: '(file_path\\?"\s*:\s*\\?"[^"\\]*|(cat|sed|head|less)\s[^"\\]*)branch-pr/references/review-policy\.md'
match: contains
target: trace
arm: both
---
