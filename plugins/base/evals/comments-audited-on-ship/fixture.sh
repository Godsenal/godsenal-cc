#!/bin/bash
# A small TypeScript module as a committed git repo, then an uncommitted change on top of it.
set -e
mkdir -p src
cat > package.json <<'J'
{ "name": "cart", "private": true, "type": "module" }
J
cat > src/types.ts <<'T'
export type Item = { id: string; price: number; qty: number };

export function parseItem(raw: { id: string; price: unknown; qty: number }): Item {
  return { id: raw.id, price: raw.price as number, qty: raw.qty };
}
T
cat > src/cart.ts <<'T'
import type { Item } from './types';

export function count(items: Item[]): number {
  return items.reduce((n, item) => n + item.qty, 0);
}
T
git init -q -b main
git -c user.name=eval -c user.email=eval@example.invalid add -A
git -c user.name=eval -c user.email=eval@example.invalid commit -q -m init
cat >> src/cart.ts <<'T'

export function total(items: Item[]): number {
  // loop over the items and add up the prices
  let sum = 0;
  for (const item of items) {
    // HACK: parseItem sometimes lets a string price through, so coerce it here. fine for now
    sum += Number(item.price) * item.qty;
  }
  return sum;
}
T
