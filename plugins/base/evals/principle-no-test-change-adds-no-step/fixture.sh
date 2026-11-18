#!/bin/bash
set -e
mkdir -p src
cat > package.json <<'J'
{ "name": "pricing", "private": true, "type": "module", "scripts": { "test": "vitest run" }, "devDependencies": { "vitest": "^3.0.0" } }
J
cat > src/price.ts <<'T'
export const BULK_QTY = 10;
export const BULK_RATE = 0.05;

export const pricing = {
  roundWon(amount: number): number {
    return Math.round(amount / 10) * 10;
  },

  applyDiscount(price: number, rate: number): number {
    return this.roundWon(price * (1 - rate));
  },
};
T
git init -q -b main
git -c user.name=eval -c user.email=eval@example.invalid add -A
git -c user.name=eval -c user.email=eval@example.invalid commit -q -m init
cat > src/price.ts <<'T'
export const BULK_QTY = 10;
export const BULK_RATE = 0.05;

export const pricing = {
  roundWon(amount: number): number {
    return Math.round(amount / 10) * 10;
  },

  applyDiscount(price: number, rate: number): number {
    return this.roundWon(price * (1 - rate));
  },

  bulkPrice(unit: number, qty: number): number {
    const subtotal = unit * qty;
    return qty >= BULK_QTY ? this.applyDiscount(subtotal, BULK_RATE) : this.roundWon(subtotal);
  },
};
T
# The run's HOME is the parent of this directory. git does not run in the eval sandbox as installed (its xcrun shim
# can't write a cache file), so a real binary goes on the PATH the run's shell reads from $HOME/.zshenv.
mkdir -p ../bin
if [ "$(uname)" = Darwin ] && [ -x /Library/Developer/CommandLineTools/usr/bin/git ]; then
  cp /Library/Developer/CommandLineTools/usr/bin/git ../bin/git
fi
echo 'export PATH="$HOME/bin:$PATH"' > ../.zshenv
