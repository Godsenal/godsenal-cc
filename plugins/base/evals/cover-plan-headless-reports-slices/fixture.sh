#!/bin/bash
set -e
mkdir -p src
cat > package.json <<'J'
{ "name": "memo-cli", "private": true, "type": "module", "bin": { "memo": "src/cli.mjs" } }
J
cat > src/store.mjs <<'T'
import { readFileSync, writeFileSync, existsSync } from 'node:fs';

const FILE = process.env.MEMO_FILE ?? 'memos.json';

export function load() {
  return existsSync(FILE) ? JSON.parse(readFileSync(FILE, 'utf8')) : [];
}

export function save(memos) {
  writeFileSync(FILE, JSON.stringify(memos, null, 2));
}
T
cat > src/cli.mjs <<'T'
#!/usr/bin/env node
import { load, save } from './store.mjs';

const [cmd, ...rest] = process.argv.slice(2);
const memos = load();
if (cmd === 'add') {
  memos.push({ id: memos.length + 1, text: rest.join(' '), at: new Date().toISOString() });
  save(memos);
} else if (cmd === 'list') {
  for (const m of memos) console.log(`${m.id}. ${m.text}`);
} else {
  console.log('usage: memo add <text> | memo list');
}
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
