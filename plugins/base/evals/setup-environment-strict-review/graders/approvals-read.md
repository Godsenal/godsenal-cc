---
type: regex
pattern: '(file_path\\?"\s*:\s*\\?"[^"\\]*|(cat|sed|head|less)\s[^"\\]*)\.claude/approvals\.yml'
match: contains
target: trace
arm: both
---
