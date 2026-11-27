---
type: regex
pattern: '\b(?:attempt\w*|retr\w*|tries)\b|<=?\s*[23]\b'
flags: i
match: contains
target: { source: file, path: src/screens/Settings.tsx }
arm: both
---
