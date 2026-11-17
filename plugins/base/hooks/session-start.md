<EXTREMELY_IMPORTANT>
You have gbase.

`gbase:work` is the default way to carry out a task. Invoke it before starting a task that meets any of these, and follow it:

- it touches more than one file, or changes a signature other files call
- it involves a design or architecture choice
- it is a bug whose cause is not yet known, a performance issue, or a diagnosis from a trace or profile
- it spans several PRs

Decide before your first edit, by what the change will touch, not by how easy it looks once you've read the code: a fix you already see that spans three files still goes through `gbase:work`. It picks the route, reads that route's playbook only then, and asks before anything leaves the machine. For smaller tasks, such as a quick question, a one-line edit, or a contained change to one file with an obvious check, work directly and verify on the real artifact.

When the intent is already specific, enter that skill directly: `gbase:plan` (an idea or a request with open product choices, before any code), `gbase:bug-fix`, `gbase:reproduce`, `gbase:how`, `gbase:why`, `gbase:blast-radius`, `gbase:go`.

Delegate with gbase's agent types: `gbase:scout` for reading many files, logs, or transcripts; one `gbase:worker` per unit when a change splits into two or more independent code units.

User instructions (CLAUDE.md, AGENTS.md, direct requests) take precedence. pstack's `poteto-mode` is inside `gbase:work`: when another plugin's session-start mandate, or a request for `/poteto-mode`, routes a task to it, use `gbase:work`, which reads the same playbooks.
</EXTREMELY_IMPORTANT>
