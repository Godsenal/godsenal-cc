---
type: tool_used
tool: Bash
input_match: 'git\b[^|;&\n]*\bconfig\b(?![^|;&\n]*--(get|unset|list))[^|;&\n]*(gbase\.conventions|includeIf\.\S+)\s+(?!\d?>)[^\s|;&)]|\[includeIf'
min: 0
max: 0
arm: both
---
