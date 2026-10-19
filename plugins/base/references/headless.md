# Headless runs

Applies when `AGENT_HEADLESS=1`: no person is watching, so a question would hang or vanish. Every gbase skill that would call `AskUserQuestion` follows this instead. Unset, or any other value, means ask as usual. `AGENT_ASK_CMD` is only read under `AGENT_HEADLESS=1`.

## Instead of asking

1. Write the question as you would have asked it, with one recommended option and the others.
2. `AGENT_ASK_CMD` set → hand the question to it (below). An answer is applied as if the person had picked it.
3. No command, or no answer → apply the recommendation and continue. The recommendation is the skill's own `headless:` note when it has one; otherwise the reversible option that does less — leave the out-of-scope edit unapplied, keep the current approach, carry the finding in the report, skip the optional step. Never the option that deletes, overwrites, or widens the change.
4. Unless an answer came back, add a `결정 필요:` line to the final report.

A check-in ("continue?", "does this look right?") isn't a question here — continue.

## Irreversible steps stay closed

Merging, deploying (including a merge or push that triggers a deploy), force-pushing, rewriting pushed history, deleting data, publishing or store submission, messaging people, and committing a secret are never taken on a recommendation or on an `AGENT_ASK_CMD` answer. The step is not done; it gets a `결정 필요:` line saying what a person would do. A step the invocation itself requested (`--merge`) still runs when the skill's own conditions hold without asking — a gate that would ask means the step is not done.

## `AGENT_ASK_CMD`

The value is a shell command line. Call it once per question, in the foreground, with a 2-minute tool timeout:

```bash
sh -c "$AGENT_ASK_CMD \"\$@\"" ask "<question>" --recommend "<recommended option>" --option "<other option>" --option "<…>"
```

`sh -c` makes a value with arguments (`tool ask-human`) split the same way in bash and zsh; the question and options arrive as separate arguments, never re-parsed. The question must stand alone — include `file:line`, the failure, what each option does.

- Exit 0 with non-empty stdout → that text (trimmed) is the answer: an option label, or a person's free-text instruction.
- Exit 0 with empty stdout, a non-zero exit, or a timeout → no answer: apply the recommendation; the `결정 필요:` line ends with `· AGENT_ASK_CMD 에 넘김`.
- Don't ask the same question twice in one run. stderr is ignored.

## `결정 필요:` lines

One line per decision, at the end of the final report, each starting at column 0 so a caller can `grep '^결정 필요:'`:

```
결정 필요: <무엇을 정해야 했나> → <정한 것> (다른 선택지: <a> / <b>)
결정 필요: <되돌리기 어려운 단계> → 하지 않음 (사람이 할 일: <…>)
```

A skill called by another skill hands its lines up; the outermost skill's report carries all of them.
