# Repo conventions

gbase runs in repos that have their own rules for branches, commits, and PRs (a company repo), and in repos that have none. `branch-pr` (branch, commits, PR), `monitor` (merge), and `gbase-run` (its worktree branch) take each value below from the first source that has one, and use the gbase default only when none does.

## Order

1. **The request.** What the user or caller asked for in this task.
2. **The repo's own settings.** Its instruction files (`CLAUDE.md`, `AGENTS.md`, `CONTRIBUTING.md`, `.github/CONTRIBUTING.md`), PR templates, and the config a hook or CI enforces (commitlint, a commit-msg or pre-push hook, a branch-name check in a workflow), plus GitHub's repo settings. Teammates and CI hold the repo to these, so they come before anything of the user's.
3. **The user's environment file.** `git config --get gbase.conventions` prints the path of a markdown file that says how work is done in that environment. Its `## Conventions` section holds these values; the rest says where tickets are read and what may be written back ([environment.md](environment.md)). Read it before the first branch, commit, or PR of the task. It covers what the repo doesn't write down. `gbase:setup` drafts it from the repo and the session's tools, so nobody has to write it by hand.
4. **The repo's history.** What the last 10 to 20 merged PRs, commits, and branches did, when they agree. One or two odd ones don't make a convention.
5. **The gbase default** in the table.

Steps 1 to 3 are the settings; "settings only" in the table means history doesn't count.

Git config reaches every checkout and gbase worktree of a repo, and with `includeIf` a whole folder of repos, so a company's rules can be set once without touching its repos:

```ini
# ~/.gitconfig
[includeIf "gitdir:~/work/"]
    path = ~/work/.gitconfig

# ~/work/.gitconfig
[gbase]
    conventions = ~/work/gbase-environment.md
    branchPrefix = feature/
```

A parent-folder `CLAUDE.md` doesn't do this: `gbase-run` worktrees live under `$GBASE_HOME/worktrees`, outside that folder.

## Values

| Value | Read the convention from | gbase default |
|---|---|---|
| Branch name | `git branch -r --sort=-committerdate`, `gh pr list --state merged --json headRefName` | `feat/` `fix/` `refactor/` `docs/` `chore/` + slug (`branch-pr`); `gbase/<name>` for a `gbase-run --worktree` run |
| Commit message | `git log --format=%s -20` (format, language, ticket key, scope) | conventional commits |
| PR title | `gh pr list --state merged --limit 15 --json title` | the change in one Korean line |
| PR body | the repo's PR template | `branch-pr`'s body |
| PR language | the merged PRs' bodies | Korean, section headings in English (the `## 출력 언어` block) |
| Ticket or issue reference | the key pattern in branch names, titles, and commits (`ABC-123`, `#123`, `Closes #123`) | none |
| Labels, reviewers, assignees | settings only; CODEOWNERS assigns reviewers on GitHub's side | none |
| Draft or ready | settings only | ready, unless `--draft` was passed |
| Preview before the PR | settings only; `ship-prep` reads the environment file's `before the PR: preview` line ([environment.md](environment.md)) | none: the PR opens |
| Replies on the PR | settings only; `pr-status` reads the environment file's `review replies: draft` line ([environment.md](environment.md)) | posted: monitor replies to each comment it handles |
| Base branch | `gh repo view --json defaultBranchRef` (`origin/HEAD`) | `origin/main`, then `origin/master` |
| Merge method, branch deletion | `gh repo view --json squashMergeAllowed,mergeCommitAllowed,rebaseMergeAllowed,deleteBranchOnMerge`, then recent merges | squash, `--delete-branch` |
| Screenshots in a PR | settings only | uploaded to the repo's `gbase-assets` branch |

## Rules

- **Never invent a ticket key or issue number.** A convention that needs one takes it from the request, the branch, or the pause note. With none there, ask; headless, leave it out and add a `결정 필요:` line ([headless.md](headless.md)). What a ticket says is never guessed either: it is fetched by the environment file's method or reported as not read ([environment.md](environment.md)).
- **The runner only reads `gbase.branchPrefix`.** It can't read instructions or history, so a `--worktree <name>` branch is `<prefix><name>`. When the repo also needs a ticket key in the name, the caller puts it in `<name>`.
- **A rule that clashes with a gbase contract** keeps the contract and follows the rule only where it reaches. The pause commit's `wip:` subject stays because it is never pushed, and the PR template still gets `Review focus` and `Evidence`.
- Say which source set a value only when it isn't the gbase default, in one line of the report (`브랜치 이름: CONTRIBUTING.md 규칙 따름`).
