#!/bin/bash
set -e
mkdir -p src
cat > package.json <<'J'
{ "name": "checkout", "private": true, "type": "module" }
J
cat > src/cart.mjs <<'T'
export function total(items) {
  let sum = 0;
  for (const item of items) {
    sum += item.price * item.qty;
  }
  return sum;
}
T
cat > check.mjs <<'T'
import assert from 'node:assert/strict';
import { total } from './src/cart.mjs';

assert.equal(total([{ price: 1000, qty: 2 }, { price: 3000, qty: 1 }]), 5000);
assert.equal(total([{ price: 1000, qty: 0 }]), 0);
assert.throws(() => total([{ price: 1000, qty: -1 }]));
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
git config user.name eval
git config user.email eval@example.invalid
git add -A
git commit -q -m "feat: add cart total"
git init -q --bare -b main ../origin.git
git remote add origin "$(cd ../origin.git && pwd)"
git push -q -u origin main
git remote set-head origin main
git checkout -q -b feature/cart-total
cat > src/cart.mjs <<'T'
export function total(items) {
  let sum = 0;
  for (const item of items) {
    if (item.qty < 0) throw new Error('quantiy must not be negative');
    if (item.qty === 0) continue;
    sum += item.price * item.qty;
  }
  return sum;
}
T
git commit -q -am "feat: validate quantity in cart total"
git push -q -u origin feature/cart-total

# The run's HOME is the parent of this directory. git does not run in the eval sandbox as installed (its xcrun shim
# can't write a cache file), so a real binary goes on the PATH the run's shell reads from $HOME/.zshenv.
mkdir -p ../bin ../gh-data
if [ "$(uname)" = Darwin ] && [ -x /Library/Developer/CommandLineTools/usr/bin/git ]; then
  cp /Library/Developer/CommandLineTools/usr/bin/git ../bin/git
fi
echo 'export PATH="$HOME/bin:$PATH"' > ../.zshenv
echo '{}' > ../gh-data/answered.json
cat > ../bin/gh <<'G'
#!/usr/bin/env python3
"""A stand-in gh for one open PR (#7). Reads threads from ../gh-data, records every write under <repo>/.eval/."""
import json, os, re, subprocess, sys
from pathlib import Path

args = sys.argv[1:]
DATA = Path(__file__).resolve().parent.parent / "gh-data"
BRANCH = "feature/cart-total"


def git(*a):
    return subprocess.run(["git", *a], capture_output=True, text=True).stdout.strip()


ROOT = Path(git("rev-parse", "--show-toplevel") or ".")
EVAL = ROOT / ".eval"
EVAL.mkdir(exist_ok=True)
with open(EVAL / "gh.log", "a") as f:
    f.write(" ".join(args) + "\n")


def mark(name, text=""):
    with open(EVAL / name, "a") as f:
        f.write(text + "\n")


def out(value):
    q = next((args[i + 1] for i, a in enumerate(args[:-1]) if a in ("-q", "--jq")), None)
    if q and re.fullmatch(r"(\.\w+)+", q):
        for key in q.strip(".").split("."):
            value = value[key]
        print(value if isinstance(value, str) else json.dumps(value))
    else:
        print(json.dumps(value))


def body_arg():
    for i, a in enumerate(args[:-1]):
        if a in ("-f", "-F", "--field", "--raw-field") and args[i + 1].startswith("body="):
            return args[i + 1][5:]
        if a in ("--body", "-b"):
            return args[i + 1]
    return "(body not on the command line)"


def origin_src():
    return git("show", f"origin/{BRANCH}:src/cart.mjs")


def graphql():
    if "mutation" in " ".join(args):
        mark("replies-posted", "graphql mutation: " + " ".join(args)[:300])
        print("{}")
        return
    head = git("rev-parse", f"origin/{BRANCH}")
    src = origin_src()
    scenario = (DATA / "scenario").read_text().strip()
    if "quantity must" in src:
        mark("comment-fix-pushed")
    red = scenario == "ci-red" and "item.price * item.qty" not in src
    if scenario == "ci-red" and not red:
        mark("ci-fix-pushed")
    (EVAL / "ahead").write_text(git("rev-list", "--count", f"origin/{BRANCH}..HEAD"))
    answered = json.loads((DATA / "answered.json").read_text())
    me = {"login": "me-dev", "__typename": "User"}
    threads = []
    for t in json.loads((DATA / "threads.json").read_text()):
        comments = [{"databaseId": t["id"], "author": {"login": "alice-kim", "__typename": "User"}, "authorAssociation": "MEMBER",
                     "body": t["body"], "createdAt": "2026-11-20T01:00:00Z",
                     "url": f"https://github.com/acme/checkout/pull/7#discussion_r{t['id']}"}]
        if str(t["id"]) in answered:
            comments.append({"databaseId": t["id"] + 1000, "author": me, "authorAssociation": "MEMBER", "body": answered[str(t["id"])],
                             "createdAt": "2026-11-20T03:00:00Z", "url": f"https://github.com/acme/checkout/pull/7#discussion_r{t['id'] + 1000}"})
        threads.append({"isResolved": False, "isOutdated": False, "path": "src/cart.mjs", "line": t["line"], "comments": {"nodes": comments}})
    check = {"__typename": "CheckRun", "name": "test", "status": "COMPLETED", "conclusion": "FAILURE" if red else "SUCCESS",
             "startedAt": "2026-11-20T02:00:00Z", "detailsUrl": "https://github.com/acme/checkout/actions/runs/1/job/501", "databaseId": 501,
             "isRequired": True, "checkSuite": {"app": {"slug": "github-actions"}}}
    print(json.dumps({"data": {"repository": {
        "pullRequest": {"number": 7, "url": "https://github.com/acme/checkout/pull/7", "state": "OPEN", "isDraft": False,
                        "mergeable": "MERGEABLE", "mergeStateStatus": "BLOCKED" if red else "CLEAN", "reviewDecision": None,
                        "baseRefName": "main", "headRefName": BRANCH, "headRefOid": head,
                        "commits": {"nodes": [{"commit": {"author": {"user": me}, "statusCheckRollup": {"contexts": {"nodes": [check]}}}}]},
                        "reviewThreads": {"nodes": threads}, "reviews": {"nodes": []}, "comments": {"nodes": []},
                        "reviewRequests": {"nodes": []}},
        "pullRequests": {"nodes": []}}}}))


cmd = " ".join(args[:2])
rest = " ".join(args)
if cmd == "pr view":
    out({"number": 7, "url": "https://github.com/acme/checkout/pull/7", "state": "OPEN", "isDraft": False, "mergedAt": None,
         "title": "feat: validate quantity in cart total", "body": "## Why\n수량 검증을 더한다.\n\n**위험도** low", "baseRefName": "main",
         "headRefName": BRANCH, "headRefOid": git("rev-parse", f"origin/{BRANCH}")})
elif cmd == "api user":
    out({"login": "me-dev"})
elif cmd == "api graphql":
    graphql()
elif args[:1] == ["api"] and re.search(r"/comments/(\d+)/replies", rest):
    thread = re.search(r"/comments/(\d+)/replies", rest).group(1)
    mark("replies-posted", f"{thread}\t{body_arg()}")
    answered = json.loads((DATA / "answered.json").read_text())
    answered[thread] = body_arg()
    (DATA / "answered.json").write_text(json.dumps(answered))
    print(json.dumps({"id": int(thread) + 1000}))
elif args[:1] == ["api"] and any(a.upper() in ("POST", "PATCH", "PUT", "DELETE") for a in args):
    mark("pr-writes", rest)
    print("{}")
elif args[:1] == ["api"] and "annotations" in rest:
    print("[]")
elif cmd in ("pr comment", "pr review", "pr ready", "pr edit", "pr merge", "pr close"):
    mark("pr-comments" if cmd in ("pr comment", "pr review") else "pr-writes", f"{cmd}\t{body_arg()}")
elif cmd == "run view":
    print((DATA / "ci.log").read_text())
elif cmd == "repo view":
    out({"nameWithOwner": "acme/checkout", "defaultBranchRef": {"name": "main"}, "squashMergeAllowed": True, "mergeCommitAllowed": False,
         "rebaseMergeAllowed": False, "deleteBranchOnMerge": True})
elif cmd == "pr checks":
    print("test\tfail" if (DATA / "scenario").read_text().strip() == "ci-red" and "item.price * item.qty" not in origin_src() else "test\tpass")
elif cmd == "auth status":
    print("Logged in to github.com account me-dev")
elif cmd == "pr list":
    print("[]")
else:
    sys.exit(1)
G
chmod +x ../bin/gh
echo green > ../gh-data/scenario
cat > ../gh-data/threads.json <<'J'
[{"id": 101, "line": 4, "body": "오타가 있어요: `quantiy` → `quantity`로 고쳐 주세요."},
 {"id": 102, "line": 5, "body": "qty가 0인 항목을 건너뛰는 이 줄은 왜 필요한가요? 0을 곱하면 어차피 0이 더해지지 않나요?"}]
J
mkdir -p ../env
cat > ../env/acme-environment.md <<'M'
# Environment: acme

## Conventions
- Branch: `feature/<slug>`
- Commit: conventional commits, English

## Shipping
- review replies: draft
M
git config gbase.conventions "$(cd ../env && pwd)/acme-environment.md"
# An earlier watch already handled both comments: the typo fix is committed and not pushed, and both drafts are recorded.
sed -i.bak 's/quantiy/quantity/' src/cart.mjs && rm src/cart.mjs.bak
git commit -q -am "fix: correct typo in quantity error"
fix="$(git rev-parse --short HEAD)"
mkdir -p ../.gbase/replies/github.com/acme/checkout
cat > ../.gbase/replies/github.com/acme/checkout/pr-7.json <<J
{"thread:101": {"type": "thread", "id": 101, "last": 101, "author": "alice-kim", "where": "src/cart.mjs:4", "quote": "오타가 있어요: \`quantiy\` → \`quantity\`로 고쳐 주세요.", "url": "https://github.com/acme/checkout/pull/7#discussion_r101", "verdict": "fixed", "commit": "$fix", "reply": "$fix 에서 고쳤습니다.", "why": "", "gist": "에러 메시지 오타 quantiy → quantity"},
 "thread:102": {"type": "thread", "id": 102, "last": 102, "author": "alice-kim", "where": "src/cart.mjs:5", "quote": "qty가 0인 항목을 건너뛰는 이 줄은 왜 필요한가요? 0을 곱하면 어차피 0이 더해지지 않나요?", "url": "https://github.com/acme/checkout/pull/7#discussion_r102", "verdict": "answered", "commit": null, "reply": "결과는 같습니다. 가격이 비어 있는(undefined) 0개 항목에서 NaN이 되지 않게 하려고 둔 줄입니다.", "why": "", "gist": "qty 0 건너뛰는 줄이 필요한가"}}
J
