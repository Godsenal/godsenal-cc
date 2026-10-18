# Feature map shape

The map lives in `.claude/skills/verify-<app>/features/`. It names user paths, stable handles, required state, commands, and observable proof — no implementation details.

## `features/README.md`

```markdown
# <App> verification map

Read this index before driving the app, then use the matching feature file as the recipe.

## Baseline preconditions
- Launch with a disposable data dir / test project (e.g. `DATA_DIR=/tmp/<app>-verify-$RUN_ID`).
- Seed: <named fixtures the recipes rely on>.
- Doctor must report <expected URL / bundle id / build>.
- Never drive an instance this run didn't start.

## Driving conventions
- Start every recipe from baseline unless its preconditions say otherwise.
- Accessibility labels / test IDs over CSS selectors, coordinates, or tab order.
- Restore seeded data after a mutation; never delete evidence.

## Proof
- Capture the action and the resulting state, not only the final screen.
- UI: screenshot + accessibility snapshot. CLI: command, stdout, stderr, exit code. Mutations: a second, read-only view of the stored value.
- Report an unreachable entry point with the command tried and the unmet precondition. Never report a skipped entry point as verified through another path.

## Features
- [Create a note](./create-note.md) — editor, save, cancel, persistence.
```

## One file per feature — exactly these four H2s, in order

```markdown
# Create a note

One paragraph: what the user can do, from their point of view.

## Sub-features
- `create-save` persists a title and body.
- `create-cancel` discards an unfinished draft.

## How to get to it (user POV)
- Tap `New note` in the toolbar.
- Deep link `myapp://notes/new`.

## Driving it with <harness>
Preconditions:
- Doctor passes; no note titled `Release checklist` exists.

- **Open editor.** `<exact command>` → a form labeled `Note editor` appears.
- **Save.** `<exact command>` → status `Note saved`; heading reads `Release checklist`.
- **Confirm persistence.** Reopen from the list: `<exact command>` → both values shown.
- **Proof.** `<screenshot/snapshot command> artifacts/verify/create-note/…`

## Gotchas
- A "saved" toast alone isn't proof — reopen the note from the list.
- Titles are trimmed on save; assert the rendered title, not the input value.
```

Every action bullet pairs a user action with an exact command and an observable result. A proof that drives one convenient entry point is incomplete when the map lists others.
