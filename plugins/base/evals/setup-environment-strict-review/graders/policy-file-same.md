---
type: regex
pattern: 'rules:\n  - purpose: "A change takes two people\. When Claude''s review passes, one is enough\."\n    paths: \["\*\*"\]\n    verdict: \{ claude: comments, seats: 2 \}\n    override:\n      - \{ if: "claude/code_review = pass", verdict: \{ claude: comments, seats: 1 \} \}\n$'
match: contains
target: { source: file, path: .claude/approvals.yml }
arm: both
---
