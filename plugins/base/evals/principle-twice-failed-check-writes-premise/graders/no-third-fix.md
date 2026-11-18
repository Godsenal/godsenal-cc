---
type: regex
pattern: 'SHIPPING_FEE'
match: not_contains
target: { source: file, path: dist/cart.mjs }
arm: both
---
