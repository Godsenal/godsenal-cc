# Principles

Read when a call in a `work` run hinges on one. Most are pstack leaves, `../../principle-*/SKILL.md`; read the leaf when this line doesn't settle it.

- **Smallest change that solves it.** Delete before adding; no speculative guards, options, or abstractions.
- **Fix root causes.** Fix the first place the system went wrong, not where it surfaced; a guard is a fix only when the state it handles is legitimate.
- **Root cause before smallest.** When those two disagree, the root-cause fix wins and "smallest" only picks among changes that fix it: a guard, retry, or shorter cache time over a state that should never exist solves nothing, a fix bigger than one PR ships its first slice with the rest as `남은 작업:` lines, and a stopgap the task itself prescribes ships with the root-cause fix on a `남은 작업:` line.
- **Verify in small units**, each checked before the next. **Model the domain**: a state machine, typed model, or table, not the same conditionals across files. **Test behavior, not implementation.**
- **Don't block on reversible work.** Do it and report it. Stop only for irreversible actions — deploys (including a merge that triggers one), store submits, data deletion, force-push to shared branches, messages to people — and for product calls no experiment can settle. If running something can answer the question, run it. Committing, pushing, and opening a PR are not yours to do early because they look reversible: they are Ship, and `go`'s gates decide them.
