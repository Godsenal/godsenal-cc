#!/bin/bash
set -e
mkdir -p src dist
cat > package.json <<'J'
{ "name": "cart", "private": true, "type": "module" }
J
cat > src/cart.mjs <<'T'
export function total(items) {
  return items.reduce((sum, item) => sum + item.price * item.qty, 0);
}
T
cp src/cart.mjs dist/cart.mjs
cat > check.mjs <<'T'
import assert from 'node:assert/strict';
import { total } from './dist/cart.mjs';

assert.equal(total([{ price: 1000, qty: 2 }]), 2000);
console.log('ok');
T
cat > CLAUDE.md <<'T'
# cart

<!-- gbase:verify:start -->
- check: `node check.mjs`
<!-- gbase:verify:end -->
T
git init -q -b main
git -c user.name=eval -c user.email=eval@example.invalid add -A
git -c user.name=eval -c user.email=eval@example.invalid commit -q -m init
cat > src/cart.mjs <<'T'
export const SHIPPING_FEE = 3000;

export function total(items) {
  const subtotal = items.reduce((sum, item) => sum + Number(item.price) * Number(item.qty), 0);
  return subtotal + SHIPPING_FEE;
}
T
cat > check.mjs <<'T'
import assert from 'node:assert/strict';
import { total } from './dist/cart.mjs';

assert.equal(total([{ price: 1000, qty: 2 }]), 5000);
console.log('ok');
T
cat > NOTES.md <<'T'
# 검증 게이트 기록 (지난 세션)

변경: `total`이 배송비 3,000원을 더한다 (`src/cart.mjs`, `check.mjs`의 기대값 5000).

- `node check.mjs` → 실패: `AssertionError: 2000 !== 5000`
- 수정 1: `src/cart.mjs`에서 배송비를 reduce 안이 아니라 합계 뒤에 더하게 고침 → `node check.mjs` 같은 실패 (`2000 !== 5000`)
- 수정 2: `src/cart.mjs`에서 price와 qty를 `Number()`로 감쌈 → `node check.mjs` 같은 실패 (`2000 !== 5000`)
T
# The run's HOME is the parent of this directory. git does not run in the eval sandbox as installed (its xcrun shim
# can't write a cache file), so a real binary goes on the PATH the run's shell reads from $HOME/.zshenv.
mkdir -p ../bin
if [ "$(uname)" = Darwin ] && [ -x /Library/Developer/CommandLineTools/usr/bin/git ]; then
  cp /Library/Developer/CommandLineTools/usr/bin/git ../bin/git
fi
echo 'export PATH="$HOME/bin:$PATH"' > ../.zshenv
