---
type: regex
pattern: "console\\.log\\('usage: memo add <text> \\| memo list'\\);"
match: contains
target: { source: file, path: src/cli.mjs }
arm: both
---
