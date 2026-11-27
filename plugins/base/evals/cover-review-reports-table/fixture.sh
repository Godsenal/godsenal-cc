#!/bin/bash
set -e
mkdir -p src
cat > package.json <<'J'
{ "name": "catalog", "private": true, "type": "module" }
J
cat > src/page.mjs <<'T'
// page is 0-based.
export function paginate(items, page, size) {
  return items.slice(page * size, page * size + size);
}
T
git init -q -b main
git -c user.name=eval -c user.email=eval@example.invalid add -A
git -c user.name=eval -c user.email=eval@example.invalid commit -q -m init
cat > src/page.mjs <<'T'
// page is 1-based: the first page is 1.
export function paginate(items, page, size) {
  const start = (page - 1) * size;
  return items.slice(start, start + size - 1);
}

export function pageCount(items, size) {
  return Math.ceil(items.length / size);
}
T
# The run's HOME is the parent of this directory. git does not run in the eval sandbox as installed (its xcrun shim
# can't write a cache file), so a real binary goes on the PATH the run's shell reads from $HOME/.zshenv.
mkdir -p ../bin
if [ "$(uname)" = Darwin ] && [ -x /Library/Developer/CommandLineTools/usr/bin/git ]; then
  cp /Library/Developer/CommandLineTools/usr/bin/git ../bin/git
fi
echo 'export PATH="$HOME/bin:$PATH"' > ../.zshenv
