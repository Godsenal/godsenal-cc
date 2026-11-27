---
type: regex
pattern: "return title\\.trim\\(\\)\\.toLowerCase\\(\\)\\.replace\\(/ /g, '-'\\);"
match: contains
target: { source: file, path: src/slug.mjs }
arm: both
---
