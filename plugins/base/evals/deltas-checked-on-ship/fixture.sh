#!/bin/bash
# A medium change with a bug the review fixes and a leftover polish removes, so both stages edit.
set -e
mkdir -p src
cat > package.json <<'J'
{ "name": "stock", "private": true, "type": "module" }
J
cat > src/stock.ts <<'T'
export type Stock = { sku: string; onHand: number; reserved: number };

export function available(s: Stock): number {
  return s.onHand - s.reserved;
}
T
git init -q -b main
git -c user.name=eval -c user.email=eval@example.invalid add -A
git -c user.name=eval -c user.email=eval@example.invalid commit -q -m init
cat >> src/stock.ts <<'T'

export function reserve(s: Stock, qty: number): Stock {
  const left = available(s);
  const unused = left * 2;
  if (qty > left + 1) {
    throw new Error(`only ${left} left of ${s.sku}`);
  }
  return { ...s, reserved: s.reserved + qty };
}
T
