# gbase evals

Checks that `gbase:work` loads `gbase:design-taste` when it should, and skips it when it shouldn't.

| case | expects |
|---|---|
| `screen-loads-design-taste` | a screen change loads `design-taste` before the first `Edit` |
| `figma-given-skips-design-taste` | a task that hands over a Figma design does not load it |
| `logic-only-skips-design-taste` | a logic-only edit inside a UI file does not load it |

Run from `plugins/base` (about 1 minute and $2 for 3 runs per case):

```bash
claude plugin eval . --ablation none --scaffold --trust-plugin --allow-tools Edit Write --no-publish --threshold 0.67
```

Seen on 1.44.2: `screen-loads` and `logic-only` passed every run; `figma-given` passed 8 of 10 runs, so read its score as a rate, not a gate.

Limit: an eval run loads only this plugin. gbase 1.44.0, which had no design-taste step in `work`, also passed `screen-loads-design-taste` 3 of 3 here, while 22 real work runs that edited UI files with `design-taste` available (136–156 skills in the session) loaded it 0 times. So this suite guards the three behaviors against regressions; it does not reproduce the crowded-session miss. Check that one in real runs: `skills` in `result.json`.
