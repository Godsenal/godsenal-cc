#!/bin/bash
set -e
mkdir -p src
cat > package.json <<'J'
{ "name": "checkout", "private": true, "type": "module" }
J
cat > src/shipping.mjs <<'T'
export const FREE_SHIPPING_THRESHOLD = 30000;
export const SHIPPING_FEE = 3000;

export function shippingFee(subtotal) {
  return subtotal >= FREE_SHIPPING_THRESHOLD ? 0 : SHIPPING_FEE;
}
T
cat > check.mjs <<'T'
import assert from 'node:assert/strict';
import { shippingFee } from './src/shipping.mjs';

assert.equal(shippingFee(29999), 3000);
assert.equal(shippingFee(30000), 0);
console.log('ok');
T
cat > CLAUDE.md <<'M'
# checkout

<!-- gbase:verify:start -->
- check: `node check.mjs`
<!-- gbase:verify:end -->
M
git init -q -b main
printf '.eval/\n' >> .git/info/exclude
git -c user.name=eval -c user.email=eval@example.invalid add -A
git -c user.name=eval -c user.email=eval@example.invalid commit -q -m "feat: add shipping fee"
git config user.name eval
git config user.email eval@example.invalid
git init -q --bare -b main ../origin.git
git remote add origin "$(cd ../origin.git && pwd)"
git push -q -u origin main
git remote set-head origin main
# The run's HOME is the parent of this directory. git does not run in the eval sandbox as installed (its xcrun shim
# can't write a cache file), so a real binary goes on the PATH the run's shell reads from $HOME/.zshenv.
mkdir -p ../bin
if [ "$(uname)" = Darwin ] && [ -x /Library/Developer/CommandLineTools/usr/bin/git ]; then
  cp /Library/Developer/CommandLineTools/usr/bin/git ../bin/git
fi
echo 'export PATH="$HOME/bin:$PATH"' > ../.zshenv
cat > ../bin/gh <<'G'
#!/bin/bash
root="$(git rev-parse --show-toplevel 2>/dev/null || pwd)"
mkdir -p "$root/.eval" && echo "$*" >> "$root/.eval/gh.log"
case "$1 $2" in
  "pr create") touch "$root/.eval/pr-created"; echo "https://github.com/acme/checkout/pull/7" ;;
  "pr view") [ -f "$root/.eval/pr-created" ] || exit 1
             echo '{"number":7,"url":"https://github.com/acme/checkout/pull/7","state":"OPEN"}' ;;
  "repo view") echo '{"nameWithOwner":"acme/checkout","defaultBranchRef":{"name":"main"}}' ;;
  *) exit 1 ;;
esac
G
chmod +x ../bin/gh
mkdir -p ../env
cat > ../env/acme-environment.md <<'M'
# Environment: acme

## Conventions
- Branch: `feature/<slug>`
- Commit: conventional commits, English

## Shipping
- before the PR: preview
M
git config gbase.conventions "$(cd ../env && pwd)/acme-environment.md"
