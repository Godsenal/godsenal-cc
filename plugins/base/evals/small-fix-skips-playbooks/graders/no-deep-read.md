---
type: regex
pattern: '"(?:file_path|command|path)"\s*:\s*"(?:[^"\\]|\\.)*(?:poteto-mode/playbooks/|skills/principle-|figure-it-out/|interrogate/|architect/|arena/|swarm/)'
match: not_contains
target: trace
arm: both
---
