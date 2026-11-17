# Local mode

Read when the args start with `Ship-owner: orchestrator; PR-body-file: <path>` (`gbase:go` under `AGENT_SHIP_OWNER=orchestrator`). Another program pushes the branch and opens the PR; this run prepares both and touches no remote.

- **Start with `ship-prep start --local`.** It asks nothing about the branch or the remote: the caller owns its branch. Commit on the current branch; create one only when the script says it is the default branch.
- **Already committed:** a clean tree with commits ahead of the base has no commit step. The script says so, and it is not "nothing to ship".
- **Body:** Step 4 as written, to the given path (`mkdir -p` its directory; overwrite). Run `compat-check` on the range the script prints (`<base>...HEAD`; base = `origin/<default>` when it exists, else the local default branch).
- **Remote untouched:** no `ship-prep open`, no `gh pr create`, no `ship-prep assets`. Embed each screenshot as `![<label>](<absolute local path>)` so the caller can upload it and rewrite the link. Check the draft with `ship-prep check <path> --local`.
- **Report** the lines the caller greps: `ship: local <branch> @<short-sha> — <n> commits, not pushed` and `PR 본문 초안: <path>` ([format](../../../references/orchestrator.md#report-lines)). Not pushing is the contract, not a decision: no `결정 필요:` line for the push or the PR.
