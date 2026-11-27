#!/bin/bash
set -e
mkdir -p src
cat > package.json <<'J'
{ "name": "checkout", "private": true, "type": "module" }
J
cat > src/cart.mjs <<'T'
export function subtotal(items) {
  return items.reduce((sum, item) => sum + item.price * item.qty, 0);
}
T
cat > check.mjs <<'T'
import assert from 'node:assert/strict';
import { subtotal } from './src/cart.mjs';

assert.equal(subtotal([{ price: 1000, qty: 2 }]), 2000);
console.log('ok');
T
cat > CLAUDE.md <<'M'
# checkout

<!-- gbase:verify:start -->
- check: `node check.mjs`
<!-- gbase:verify:end -->
M
git init -q -b main
git -c user.name=eval -c user.email=eval@example.invalid add -A
git -c user.name=eval -c user.email=eval@example.invalid commit -q -m init
cat > src/coupon.mjs <<'T'
const COUPONS = { WELCOME10: { percent: 10 }, FLAT3000: { amount: 3000 } };

export function applyCoupon(subtotal, code) {
  const coupon = COUPONS[code];
  if (!coupon) return subtotal;
  const off = coupon.percent ? Math.floor((subtotal * coupon.percent) / 100) : coupon.amount;
  return subtotal - off;
}
T
cat >> check.mjs <<'T'

import { applyCoupon } from './src/coupon.mjs';
assert.equal(applyCoupon(20000, 'WELCOME10'), 18000);
assert.equal(applyCoupon(20000, 'NOPE'), 20000);
T
# The run's HOME is the parent of this directory. git does not run in the eval sandbox as installed (its xcrun shim
# can't write a cache file), so a real binary goes on the PATH the run's shell reads from $HOME/.zshenv.
mkdir -p ../bin
if [ "$(uname)" = Darwin ] && [ -x /Library/Developer/CommandLineTools/usr/bin/git ]; then
  cp /Library/Developer/CommandLineTools/usr/bin/git ../bin/git
fi
echo 'export PATH="$HOME/bin:$PATH"' > ../.zshenv
