# Setup: the environment file

Read at setup's "5. Environment file". It finds out how work is done around this repo and records it once in the user's environment file, whose format and rules are in [environment.md](../../../references/environment.md). Explore, show what was found, confirm, then write. Nothing here is written into the repo.

## 1. Explore

Read-only. Ask nothing that one of these answers.

| Look at | It tells you |
|---|---|
| `git remote -v` | the forge and the owner; a self-hosted host or an organization is a work environment |
| `git config --show-origin --get gbase.conventions` | a file already set. Update it in place, don't make a second one |
| instruction files, PR template, `CONTRIBUTING`, commitlint config, git hooks, a branch or title check in CI | rules the repo already enforces. They come before the environment file ([conventions.md](../../../references/conventions.md)), so the draft doesn't repeat them |
| the last 20 merged PRs (title, head branch, body), `git log --format=%s -30`, remote branch names | the formats that agree, a ticket key pattern (`ABC-123`, `#123`, `Closes #123`), tracker links in PR bodies |
| the session's tools: MCP servers and their tool names, issue-tracker CLIs on `PATH` (`command -v gh glab acli` and whatever the history's links point to) | how a ticket can be read from here |
| `CODEOWNERS` (root, `.github/`, `docs/`), the last 20 merged PRs' reviewers, `labels`, and commit trailers (`gh pr list --state merged --limit 20 --json latestReviews,reviewRequests,labels`: a request is gone once its review is in, so who reviewed is `latestReviews`; `git log -30 --format='%h %(trailers:key=Signed-off-by,valueonly,separator=%x2C )'`), the merged PRs' sizes (`additions`, `deletions`) | who reviews and which labels every PR gets, whether commits carry a DCO sign-off, and how large PRs here run: the `review-policy.md` lines below |
| `git ls-files '*.claude/approvals.yml'` and each file it lists, read only (the `claude-approvals` skill has the format: a top `mode: observe` decides nothing, each rule's `verdict` has `claude` and `seats`) | that the "Claude Approvals" check, not a reviewer list, decides who approves the files its rules cover |
| branch protection and rulesets of the default branch (`gh api repos/<owner>/<repo>/branches/<default>/protection`, `gh api repos/<owner>/<repo>/rules/branches/<default>`; a 403 or 404 means not readable, not "none") | required approvals (`required_approving_review_count`, a `pull_request` rule), signed commits (`required_signatures`, a `required_signatures` rule), linear history (`required_linear_history`, a `required_linear_history` rule) |
| `docs/adr`, `docs/rfcs`, `docs/specs`, wiki links in the instruction files and PR bodies | where the team keeps specs and decisions |

Then decide where tasks come from:

- **Keys like `ABC-123` in the history** → an external tracker. Name it from the links in PR bodies and instruction files, or from the tool that resolves a key. When nothing names it, ask in the preview which tracker it is and how the user opens a ticket, and record the answer as prose.
- **Only `#123` or `Closes #123`**, and the forge has issues turned on → the forge's own issues.
- **Neither** → no tracker. When the formats also match the gbase defaults, there is nothing to record: say so and write no file.

**Run the read method once** on a real key from the history before recording it, as the verify block does with its commands. Take the command's shape from the tool's own `--help` or the MCP tool's schema, not from memory, because a CLI's flags change between versions. Record `(ran <date>: ok)` or `(not run: <reason>)`, for example when the server needs a login only the user can do. Never run a write (comment, transition, assign, create) during setup.

**No tool here reads the tracker** → the method line says that and what the user has to connect, and stops there. Write no example command for a tool this session doesn't have, because an unrun line in the file gets run later as if it had been checked.

## 2. Draft

Fill environment.md's format with what was found.

- A line needs evidence: a file, a count of PRs that agree, a command that ran. The evidence goes in the preview, not in the file.
- `## Write-back` is `off` for every kind unless the user turns one on in the preview. A write method is recorded only for a kind that is `on` or `ask`, marked `(not run)`.
- Put no token, cookie, or password in the file. Name the environment variable or the login command.
- `## Shipping` and its lines (`before the PR: preview`, `review replies: draft`) are written only when the user picks them in step 3. Nothing in a repo shows whether its owner wants to read a change before the team sees it, or to write their own replies to reviewers, so neither is ever inferred.
- **Review policy** ([review-policy.md](../../branch-pr/references/review-policy.md)): propose `Reviewers:` only for people or a team asked on most of the 20 PRs and not already CODEOWNERS (GitHub asks those itself), `Labels:` only for a label on most of them, and `Commit sign-off: on` only when most commits carry the trailer or a DCO check runs in CI. They go into the draft unasked, as the formats do, with the count as evidence. `PR size:` is never inferred from the history, since a size the team merged is not a limit it set: propose it in the preview only when `CONTRIBUTING` or a CI check states one.
- **Strict review** (the approvals and protection rows): a required approval count needs no line, because `pr-status` reads GitHub's review state, and a policy file needs none, because `ship-prep` names it on its `approvals:` line; say what each asks in the preview, with the file or the API answer as evidence. Propose no `Reviewers:` for files a policy's `seats` or CODEOWNERS already cover. Required signed commits → no line either, since signing is git's `commit.gpgsign`: say in the preview whether it is on here, because an unsigned commit fails only on GitHub. Required linear history → `Merge: squash` (or `rebase` when only that is allowed) under `## Conventions`. **Never edit a policy file, a ruleset, or branch protection**: they are the repo's, and setup only reads them.
- The tracker is described the way the user would say it. gbase carries no template for any tracker, so a section is prose plus the commands that ran here.

## 3. Preview and ask once

Show the findings (one line each, with evidence), the whole draft, the path it will be written to, and the exact `git config` change. Then one `AskUserQuestion` call, recommended answer first, holding only the questions exploration left open:

- **Write-back**, when a tracker was found: read only (recommended) / link the PR on the ticket / link the PR and ask before moving the ticket.
- **What the team sees**, when the environment is a company's or a client's (a self-hosted host, an organization's repos): open the PR and reply to reviews as now (recommended) / show me a preview before the PR / draft the replies to review comments and let me post them / both.
- **Scope**, when the repo sits in a folder beside other repos of the same owner: that folder (recommended) / this repo only.
- **Apply**: write it / let me edit first / skip.

*headless:* no environment file is written and no git config changes. Print the draft in the report, since a worktree's git dir goes away with it, and also save it to `$(git rev-parse --absolute-git-dir)/gbase/environment-draft.md`. Add a `결정 필요:` line naming that path and the `git config` command. The draft carries no `## Shipping` section; where "What the team sees" would have been asked, the report names the two lines the user can add.

## 4. Write

- **The file.** A path already set → edit it in place and keep the user's own lines. Otherwise, folder scope → `<folder>/gbase-environment.md`; this repo only → `${XDG_CONFIG_HOME:-$HOME/.config}/gbase/<owner>-<repo>.md`. Never inside a repo. A team that wants shared rules writes them in the repo's instruction files, which already come first.
- **This repo only:** `git config --local gbase.conventions <absolute path>`. It reaches every worktree of the repo.
- **A folder:** `<folder>/.gitconfig` gets `[gbase] conventions = <absolute path>`, and the global config needs `[includeIf "gitdir:<folder>/"] path = <folder>/.gitconfig`. If `git config --global --get-regexp '^includeif\.'` already has it, nothing more. If not, don't edit `~/.gitconfig` when a dotfiles tool owns it (it is a symlink, or chezmoi, stow, yadm, or home-manager manages it). In that case write the lines into a machine-local file it already includes (`git config --global --get-all include.path`), or print them for the user to add. A plain, unmanaged `~/.gitconfig` is edited only when the preview said so.
- **Check it:** `git config --get gbase.conventions` in this repo prints the path. When the `includeIf` lines are still the user's to add, say that the file has no effect until they are.

## 5. Report

`environment file: created <path> | updated | no change | nothing to record | draft only`, `git config: local | folder (<file>) | pending — <the lines to add>`, `ticket read: ran ok | not run — <reason>`, `write-back: <the kinds turned on, or none>`, `before the PR: preview | open`, `review replies: draft | post`, `review policy: <the lines proposed, or none>`, and `strict review: <policy files and their mode, required approvals, signed commits, linear history> | none found | not readable — <reason>`.
