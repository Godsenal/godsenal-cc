#!/bin/bash
set -e
c() { git -c user.name=eval -c user.email=eval@example.invalid commit -q --allow-empty "$@"; }
mkdir -p src
echo '{ "name": "notes", "private": true }' > package.json
echo 'export const notes = [];' > src/notes.ts
git init -q -b main
git remote add origin https://github.com/acme-oss/notes.git
git add -A
c -m "chore: initial commit"
c -m "feat: add tags to notes (#9)" -m "Closes #7"
c -m "fix: keep the draft when the editor closes (#10)" -m "Closes #8"
c -m "fix: handle an empty title (#12)" -m "Closes #11"
c -m "docs: explain the sync setting (#13)"
c -m "feat: search notes by tag (#15)" -m "Closes #14"
c -m "refactor: split the storage module (#17)"
c -m "fix: sort pinned notes first (#19)" -m "Closes #18"
for b in fix/empty-title feat/search-by-tag fix/pinned-order; do git update-ref "refs/remotes/origin/$b" HEAD; done
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
case "$1 $2" in
  "auth status") echo "github.com: logged in as eval" ;;
  "repo view") echo '{"nameWithOwner":"acme-oss/notes","hasIssuesEnabled":true,"defaultBranchRef":{"name":"main"},"squashMergeAllowed":true,"mergeCommitAllowed":false,"rebaseMergeAllowed":false,"deleteBranchOnMerge":true}' ;;
  "pr list") echo '[{"number":19,"title":"fix: sort pinned notes first","headRefName":"fix/pinned-order","body":"Closes #18"},{"number":17,"title":"refactor: split the storage module","headRefName":"refactor/storage-split","body":""},{"number":15,"title":"feat: search notes by tag","headRefName":"feat/search-by-tag","body":"Closes #14"},{"number":12,"title":"fix: handle an empty title","headRefName":"fix/empty-title","body":"Closes #11"}]' ;;
  "issue view") echo '{"number":'"$3"',"title":"Pinned notes are not sorted first","state":"CLOSED","body":"Pinned notes should come before the rest.\n\n- [ ] pinned notes first\n- [ ] newest first within each group","comments":[]}' ;;
  "issue list") echo '[{"number":21,"title":"Export notes as markdown","state":"OPEN"}]' ;;
  *) echo "gh: this stand-in only reads (auth status, repo view, pr list, issue view, issue list)" >&2; exit 1 ;;
esac
G
chmod +x ../bin/gh
