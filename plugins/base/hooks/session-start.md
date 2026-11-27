<EXTREMELY_IMPORTANT>
You have gbase.

`gbase:work` is the default way to carry out a task. Invoke it before starting a task that meets any of these, and follow it:

- it touches more than one file, or changes a signature other files call
- it involves a design or architecture choice
- it is a bug whose cause is not yet known, a performance issue, or a diagnosis from a trace or profile
- it spans several PRs

Decide before your first edit, by what the change will touch, not by how easy it looks once you've read the code: a fix you found in the code that spans three files still goes through `gbase:work`. It asks before anything leaves the machine. For smaller tasks, such as a quick question, a one-line edit, a contained change to one file with an obvious check, or a change whose files, fix, and check the request itself already spells out, work directly, verify on the real artifact, and ship only when asked, through `gbase:go`.

A specific intent enters its skill directly: `gbase:plan` (an idea or open product choices, before code), `gbase:bug-fix`, `gbase:reproduce`, `gbase:how`, `gbase:why`, `gbase:blast-radius`, `gbase:go`. Delegate reading to `gbase:scout` and each independent code unit to its own `gbase:worker`. User instructions win; a route to pstack's `poteto-mode` means `gbase:work`.
</EXTREMELY_IMPORTANT>
