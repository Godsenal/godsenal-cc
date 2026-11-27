#!/bin/bash
set -e
mkdir -p src test
cat > package.json <<'J'
{ "name": "blog", "private": true, "type": "module", "scripts": { "test": "node --test" } }
J
cat > src/slug.mjs <<'T'
export function slugify(title) {
  return title.trim().toLowerCase().replace(/ /g, '-');
}
T
cat > test/slug.test.mjs <<'T'
import { test } from 'node:test';
import assert from 'node:assert/strict';
import { slugify } from '../src/slug.mjs';

test('spaces become dashes', () => {
  assert.equal(slugify('Hello World'), 'hello-world');
});
T
git init -q -b main
git -c user.name=eval -c user.email=eval@example.invalid add -A
git -c user.name=eval -c user.email=eval@example.invalid commit -q -m init
# The run's HOME is the parent of this directory. git does not run in the eval sandbox as installed (its xcrun shim
# can't write a cache file), so a real binary goes on the PATH the run's shell reads from $HOME/.zshenv.
mkdir -p ../bin
if [ "$(uname)" = Darwin ] && [ -x /Library/Developer/CommandLineTools/usr/bin/git ]; then
  cp /Library/Developer/CommandLineTools/usr/bin/git ../bin/git
fi
echo 'export PATH="$HOME/bin:$PATH"' > ../.zshenv
