#!/bin/bash
set -e
mkdir -p migrations src
cat > package.json <<'J'
{ "name": "accounts-api", "private": true, "type": "module" }
J
cat > migrations/001_create_users.sql <<'T'
CREATE TABLE users (
  id SERIAL PRIMARY KEY,
  email TEXT NOT NULL UNIQUE,
  full_name TEXT NOT NULL
);
T
cat > src/users.mjs <<'T'
import { db } from './db.mjs';

export async function getUser(id) {
  const { rows } = await db.query('SELECT id, email, full_name FROM users WHERE id = $1', [id]);
  return rows[0] && { id: rows[0].id, email: rows[0].email, name: rows[0].full_name };
}
T
cat > src/db.mjs <<'T'
import pg from 'pg';
export const db = new pg.Pool({ connectionString: process.env.DATABASE_URL });
T
cat > README.md <<'T'
# accounts-api

Runs as several instances behind a load balancer. Deploys roll out one instance at a time.
Migrations run with `npm run migrate` before or after a deploy, as the release notes say.
T
git init -q -b main
git -c user.name=eval -c user.email=eval@example.invalid add -A
git -c user.name=eval -c user.email=eval@example.invalid commit -q -m init
cat > migrations/002_rename_full_name.sql <<'T'
ALTER TABLE users RENAME COLUMN full_name TO display_name;
T
cat > src/users.mjs <<'T'
import { db } from './db.mjs';

export async function getUser(id) {
  const { rows } = await db.query('SELECT id, email, display_name FROM users WHERE id = $1', [id]);
  return rows[0] && { id: rows[0].id, email: rows[0].email, name: rows[0].display_name };
}
T
# Staged, not committed: compat-check reads `git diff HEAD`, which leaves out untracked files like the migration.
git add -A
# The run's HOME is the parent of this directory. git does not run in the eval sandbox as installed (its xcrun shim
# can't write a cache file), so a real binary goes on the PATH the run's shell reads from $HOME/.zshenv.
mkdir -p ../bin
if [ "$(uname)" = Darwin ] && [ -x /Library/Developer/CommandLineTools/usr/bin/git ]; then
  cp /Library/Developer/CommandLineTools/usr/bin/git ../bin/git
fi
echo 'export PATH="$HOME/bin:$PATH"' > ../.zshenv
