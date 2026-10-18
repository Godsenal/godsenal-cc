# REVIEW.md

Failure here = a skill instruction that makes an agent do the wrong thing: run a destructive git command, skip a confirmation gate, or call another skill with args it no longer understands.
Always high severity: `## Safety` sections, confirmation gates / `disable-model-invocation` on side-effecting skills (push, deploy, submit), the cross-skill contract tokens listed in `CLAUDE.md`, version fields.
A skill line that restates what the model does unprompted is a finding — it's paid on every invocation. Cap such nits at 3.
Every finding needs `file:line` evidence, not a guess from a name.
