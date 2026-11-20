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
sed -i.bak 's/FREE_SHIPPING_THRESHOLD = 30000/FREE_SHIPPING_THRESHOLD = 50000/' src/shipping.mjs && rm src/shipping.mjs.bak
sed -i.bak 's/29999/49999/; s/30000/50000/' check.mjs && rm check.mjs.bak
git checkout -q -b feature/raise-free-shipping-threshold
git add -A
git commit -q -m "feat: raise free shipping threshold to 50,000"
mkdir -p ../draft
cat > ../draft/pr-body.md <<'M'
feat: 무료 배송 기준 금액을 50,000원으로 올림

## Why
무료 배송 기준이 30,000원이라 정책이 정한 50,000원과 다릅니다. 이 PR이 들어가면 50,000원 이상 주문만 무료 배송입니다.

## Review focus
> [!NOTE]
> **사람이 판단할 곳 없음.** 기준 금액은 요청이 정했고 `check.mjs`가 새 경계값을 확인합니다.

**위험도** medium (배송비 계산 코드) · two-way · 커밋을 되돌리면 30,000원 기준으로 돌아갑니다

## Change outline
### 1. 무료 배송 기준 금액
- `FREE_SHIPPING_THRESHOLD`를 50000으로 바꿨습니다.

## Evidence
- 전에는 30,000원부터 무료 → 이제는 50,000원부터 무료
- [x] `node check.mjs` → pass (`ok`: 49,999원은 3,000원, 50,000원은 0원)

🤖 Generated with [Claude Code](https://claude.com/claude-code)
M
here="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
printf '# PR 미리보기: feat: 무료 배송 기준 금액을 50,000원으로 올림\n\n**한 줄 요약** 30,000원에서 49,999원 사이 주문에 배송비 3,000원이 붙습니다\n' |
  GBASE_HOME="$(cd .. && pwd)/.gbase" python3 "$here/../../skills/branch-pr/scripts/ship-prep" preview "$(cd ../draft && pwd)/pr-body.md" --write --reviewed > /dev/null
