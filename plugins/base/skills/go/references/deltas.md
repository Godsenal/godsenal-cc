# What one stage changed after the other looked

Read when `stage-delta` prints `next: review the polish delta` or `next: comment pass on review's fixes`. Polish and the finder run at the same time, so the finder never reads polish's edits, and review's fixes land after polish has finished. In 66 `go` runs (2026-11-17 to 26), 15 had polish code edits the finder never read (12 then watched with `monitor --no-review`, 2 with no monitor run) and 7 had review fixes polish never saw, one with two new comments the comment pass never audited. Running the stages one after the other would cost the overlap every run (median 112 s); checking only the delta costs nothing when there is none.

## `next: review the polish delta`

Polish changed lines that are not comments: Lens edits, Pass 2 restructurings, or a Pass 0 `fixed` root-cause fix. Step 3's review agent reads them, and runs even when the finder found nothing. Add to its prompt, after the findings:

```
Polish changed code after the finder read the diff: `<the diff: line>`, lines <the rows>. Before Stage 2, read that diff and add a candidate, with its failure scenario, for each hunk that may not preserve behavior; judge them with the rest.
```

With no finder findings, the args say `Findings: none` and keep `start at Stage 2` and, on `medium`, `one skeptic for low/medium`. Polish edits a review agent took this way count as reviewed: Step 6 keeps `--no-review`. When none did, Step 6 drops it for a polish `fixed` row.

## `next: comment pass on review's fixes`

A review fix added a comment, so polish's comment pass (pstack's `no-comments`) never judged it. Launch one `Agent` (`general-purpose`, `run_in_background: false`) told to `Read` `../../polish/references/comments.md` from go's base directory and run that pass only, with `risk: low`, on the rows the script printed and the diff its `diff:` line names, and to return its `Comments:` line and rows verbatim. At `low` it only deletes or keeps comments, so it changes no code a reviewer has to read again. Its `open` rows join Step 5's `Deferred:` as `low`, like polish's; a comment it deleted stays deleted.

Other cleanup on a fix (a helper the fix could reuse) is not run here: a Lens edit would be code no reviewer read. Report it as an `awaiting confirm` suggestion when the review table names one.
