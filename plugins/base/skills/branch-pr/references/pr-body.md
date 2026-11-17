# PR body: what a reviewer has to judge

Read when branch-pr's Step 4 says so. A repo's own PR template, when it has one, is the body, with `Review focus` (right under its first section) and `Evidence` added if it lacks them. The body is a briefing for a reviewer who has the diff. **The reviewer reads `Review focus` first and may stop there**, so everything a person has to judge goes in it and nowhere else; the sections below it are reference. The body's own phrases (`사람이 볼 곳`, `위험도`) follow the PR's language; Korean is only the default.

## Review focus

```markdown
## Review focus
> [!IMPORTANT]
> **사람이 볼 곳 <N>건**
> 1. **<the question, as one short bold line>** (결정)
>    `path:line` · <why no check can answer it, a few words>
> 2. **<what to look at and what "right" looks like>** (확인)
>    <where: a screenshot below, `path:line`, a device>
> 3. **<the failure, as a question>** (보류 · medium)
>    `path:line` · <failure scenario>

**위험도** <low / medium / high> (<the path or hazard that set it>) · <two-way / one-way> · <how to undo: revert the squash commit, plus anything left behind>

<details><summary>보류한 리뷰 지적 <K>건 · low 또는 기존 코드</summary>

- `path:line` <finding, one line> (low · 기존 코드)
</details>
```

N = 0 keeps the skeleton's `> [!NOTE]` line; K = 0 drops the details block.

An item is something a person must judge because no check here can. Before writing one, name what the checks would miss; if you can't, it isn't an item. Most-severe first, at most five; more than that means the PR should be split, so say so as item 1. Each item is a bold line a reviewer can answer, its kind in parentheses after the bold, and one plain line under it for where and why. Keep code spans out of the bold part:

- `(결정)` a product or design call: copy, a tradeoff the author picked, a behavior change someone may not want, a pattern other code will copy.
- `(확인)` evidence only a person can judge (how a screen looks, real data, a device), any surface the run couldn't reach (`behavior: skip`), or a `high`-tier path from the risk rule; point at the exact lines. A `Verification:` line with `differs:` is always one, titled `실기기 확인 필요: <difference>`: the check passed on another kind of input than the one that failed.
- `(보류 · <severity>)` a finding from the caller's `Deferred:` line marked `introduced` and rated `medium` or above. The rest (`low`, or `pre-existing`) go in the folded details block, marked `기존 코드` when pre-existing so they don't read as the author's fault; they never count toward N.

The alert renders as a colored box, so it stays the one thing that stands out; don't add other alert boxes elsewhere in the body.

**Two-way / one-way:** two-way when reverting the squash commit restores the old behavior. One-way when something outlives the revert: a dropped column or rewritten data, a sent notification or email, a store submission, a removed public API. Take the point of no return from compat-check's Rollback line, and add a `(확인)` item for it. If `gbase:blast-radius` ran, its confirmed risks become `(확인)` items. The risk line informs the reviewer; it never blocks the PR.

### Risk tier

When the caller passed no `Risk:` line, set the tier from the change, not the author. `gbase:go` uses the same rule:

- `high` — touches a path `REVIEW.md` marks always-high (without one: auth, payments/billing, migrations, CI/release workflows, app config like `app.json`/`eas.json`/`Info.plist`), or compat-check returned ⚠️
- `low` — docs, copy, tests, or an additive change behind a flag, and nothing above
- `medium` — everything else

## The rest of the body

`## Rollout / Deploy order` goes between Evidence and Notes, only when compat-check returned ⚠️. `## Notes` holds only what a reviewer would trip on that isn't a Review focus item (a deliberate omission, an out-of-scope find); usually empty, so drop it.

**Readable in a minute.** Every section is tables and one-line bullets, no paragraph over two lines. Short is not shorthand: never a row of nouns, arrows, or session jargon. A Change outline over ~25 lines or four groups, and any long table or command output, goes inside `<details><summary>…</summary>` with its lead line outside; if it still doesn't fit, the PR should be split.

**Pick the form per change**, for each Outline view and each Evidence pair, the one a reviewer grasps fastest:

| What changed | Show it as |
|---|---|
| How a screen looks (UI, layout, copy) | before/after screenshots side by side |
| Interaction or animation | a short GIF |
| A flow across components or services | a `mermaid` sequence diagram (GitHub renders it) |
| Logic or an algorithm | a pseudocode `diff`, plus the test that failed and now passes |
| An API, event, or RPC contract | a request/response JSON `diff` |
| Schema | a table `diff`, plus what the migration does |
| Performance | one number with its unit, before → after |
| A refactor | a file-tree `diff`, plus "the same tests pass unchanged" |
| CLI or script behavior | terminal output before/after |

A `| | Before | After |` table when Evidence has two or more pairs.

## Screenshots and GIFs

A change to what a user sees ships with the image in the body, in one place only. When the look is the change (layout, copy, a new screen), it goes in `## Change outline` as that concern's view, and Evidence says "see the screenshots above". When it proves a code change (a bug fix, a logic change), it goes in `## Evidence`.

Take them from the run's captures: the `verify-*` artifacts (`artifacts/verify/<feature>/`, gitignored) or the evidence dir in the `behavior:` lines. "After" is always available; include "before" only when the run already captured it (it reproduced the bug first). Don't relaunch the old build just for a picture. When the run took no screenshot of a UI change, take one of the after state now if the app is already running; otherwise make it a `(확인)` item. A GIF needs `ffmpeg` to convert a recording (`xcrun simctl io booted recordVideo`, Playwright video); without it, use two or three stills.

`gh` can't attach images to a PR body. Unless a setting says where images go ([conventions.md](../../../references/conventions.md)), upload them and paste the lines it prints:

```bash
ship-prep assets <file>...     # the Step 1 script; uploads to the repo's gbase-assets branch, prints ![name](url) per file
```

Never commit them to the PR branch. `ship-prep open` rejects a draft whose image is still a local path. On a public repo those images are public: only upload screens with seeded demo data, never real user data.
