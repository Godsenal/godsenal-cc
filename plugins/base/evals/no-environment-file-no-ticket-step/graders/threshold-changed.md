---
type: regex
pattern: 'FREE_SHIPPING_THRESHOLD = 50_?000'
match: contains
target: { source: file, path: src/shipping.ts }
arm: both
---
