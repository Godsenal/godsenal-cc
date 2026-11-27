---
type: regex
pattern: "SELECT id, email, display_name FROM users WHERE id = \\$1"
match: contains
target: { source: file, path: src/users.mjs }
arm: both
---
