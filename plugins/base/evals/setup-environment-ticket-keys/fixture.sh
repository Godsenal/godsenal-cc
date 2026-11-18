#!/bin/bash
set -e
c() { git -c user.name=eval -c user.email=eval@example.invalid commit -q --allow-empty "$@"; }
mkdir -p src .gitlab/merge_request_templates
echo '{ "name": "checkout", "private": true }' > package.json
echo 'export const TAX_RATE = 0.1;' > src/tax.ts
cat > .gitlab/merge_request_templates/Default.md <<'M'
## What

## Ticket
https://acme.atlassian.net/browse/PAY-

## How to test
M
git init -q -b main
git remote add origin https://git.acme-corp.example/payments/checkout.git
git add -A
c -m "PAY-88 Set up the checkout service"
for t in "PAY-91 Add tax calculation:feature/PAY-91-tax-calculation" "PAY-97 Fix rounding in tax:bugfix/PAY-97-tax-rounding" "PAY-101 Add coupon field to checkout:feature/PAY-101-coupon-field" "PAY-104 Validate coupon expiry:feature/PAY-104-coupon-expiry" "PAY-110 Fix free shipping threshold:bugfix/PAY-110-free-shipping" "PAY-112 Add order summary endpoint:feature/PAY-112-order-summary"; do
  c -m "${t%%:*}"
  git update-ref "refs/remotes/origin/${t##*:}" HEAD
  c -m "Merge branch '${t##*:}' into 'main'" -m "${t%%:*}" -m "See merge request payments/checkout!$RANDOM"
done
git update-ref refs/remotes/origin/main HEAD
# The run's HOME is the parent of this directory. git does not run in the eval sandbox as installed (its xcrun shim
# can't write a cache file), so a real binary goes on the PATH the run's shell reads from $HOME/.zshenv.
mkdir -p ../bin
if [ "$(uname)" = Darwin ] && [ -x /Library/Developer/CommandLineTools/usr/bin/git ]; then
  cp /Library/Developer/CommandLineTools/usr/bin/git ../bin/git
fi
echo 'export PATH="$HOME/bin:$PATH"' > ../.zshenv
cat > ../bin/gh <<'G'
#!/bin/bash
echo "none of the git remotes configured for this repository point to a known GitHub host" >&2
exit 1
G
chmod +x ../bin/gh
