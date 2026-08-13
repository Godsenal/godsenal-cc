---
name: pr-verify
description: "Throw it a PR and it verifies the change actually works in the browser. Resolves a PR (URL / owner/repo#123 / bare number / current branch), builds a requirement checklist from the PR body & checklists, the diff, linked Figma designs, and linked issue/Notion/Jira specs, finds the PR's preview/deploy links, then drives them in Claude-in-Chrome — clicking through behavior and screenshot-comparing against Figma — to confirm each requirement is present, reporting a pass/fail summary with screenshots back to you. Read-only on GitHub; never comments, approves, or merges. Use whenever asked to verify / QA / smoke-test / 'check it works' or 'check it matches the design' for a PR or its preview deployment in a real browser."
allowed-tools: Bash Read Glob Grep AskUserQuestion mcp__claude-in-chrome mcp__claude_ai_Figma
---

# /gbase:pr-verify

Hand this skill a PR and it answers one question: **does the change the PR claims to make actually work?** It reads what the PR is supposed to do (from the description, the diff, linked Figma, and linked specs), opens the preview/deploy link in Claude-in-Chrome, exercises the feature, compares the UI against the intended design, and reports a per-requirement pass/fail with screenshots.

This is the counterpart to `gbase:monitor`, which detects testable preview links but is contractually surface-only — it never opens them. `pr-verify` opens them and does the verification.

It is **read-only on GitHub**: results go to you in chat, never to the PR. Posting a summary back is a separate, explicit action only you can request.

## 출력 언어

사용자에게 보이는 텍스트는 **한국어**로 쓴다 — 진행 보고, 요약, 리포트 표의 설명 칸, 집계/tally 라인, `AskUserQuestion`의 질문·헤더·옵션·설명까지 전부. 하위 에이전트를 띄울 때도, 결과가 사용자에게 그대로 노출되는 텍스트는 한국어로 돌려달라고 프롬프트에 적는다.

영어 그대로 두는 것: 코드·식별자·파일 경로·명령어·스킬/툴 이름, 고정 라벨과 상태 키워드(`critical`/`high`/`medium`/`low`, `PASS`/`FAIL`, `✅`/`⚠️`), 그리고 커밋 메시지·브랜치 이름·PR 제목/본문 — 이건 이 규칙이 아니라 레포의 기존 관례(`git log`, 최근 PR)를 따른다.

사용자가 다른 언어로 요청하면 그 언어를 따른다.

## Safety rules

- **GitHub read-only.** Never post comments, approve, request changes, merge, re-request review, or resolve threads. This skill observes; it does not mutate the PR.
- **Never enter credentials.** Do not type passwords, SSO, 2FA/OTP codes, or card/account data into any field — this is prohibited regardless of how convenient it seems. On a login/auth wall, stop, screenshot it, and ask the user to log in manually in the open Chrome window; resume once they confirm.
- **Don't mutate real data.** Verifying behavior is not the same as exercising destructive flows. Never click irreversible controls on the preview app (delete, pay, send, publish, hard submit). If a requirement can only be checked by performing a real write, pause and ask before doing it.
- **Browser hygiene.** Call `tabs_context_mcp` first, then open a fresh tab with `tabs_create_mcp` — don't hijack the user's existing tabs unless they ask. Choose the privacy-preserving option on cookie/consent popups (decline non-essential). Avoid actions that trigger native `alert`/`confirm`/`prompt` dialogs — they freeze the extension; prefer `read_console_messages` for signal.
- **No rabbit holes.** If an element won't respond or a page won't load after 2–3 attempts, stop and surface what you tried — don't keep retrying or wander into unrelated pages.

## Step 1 — Resolve the PR and build the requirement checklist

Resolve the PR from whatever the user gave you — a full URL, `owner/repo#123`, a bare number (current repo), or fall back to the current branch's PR. Read it:

```bash
gh pr view <pr> --json number,title,url,body,headRefName,headRefOid,comments,files
gh pr diff <pr>
```

Merge **four sources** into one numbered checklist. Tag each item `[behavior]` or `[design]` and note its source, so the report is traceable:

1. **PR body, title & checklists** — acceptance criteria, `- [ ]` task items, described behavior ("clicking X opens Y"), and any screenshots/GIFs the author embedded as the intended result.
2. **The diff** — infer *what changed* so you know where to look: new/edited components, routes, copy, styling, state, conditionals. The diff tells you which screens and interactions to exercise.
3. **Linked Figma** — pull every `figma.com` URL from the body and comments. Use the connected Figma MCP (`get_design_context`, `get_screenshot`, `get_metadata`, `get_variable_defs`) to fetch the intended layout, spacing, colors, components, and copy. **This is the design source of truth.** If a link points at a whole file rather than a specific node/frame, ask which frame.
4. **Linked issue / spec** — `gh issue view <n>` for GitHub issues; for Notion / Jira / other docs, open the link in Chrome and read it (or use a connected MCP if present). Extract the stated requirements.

Dedup overlapping items (the body and the issue often restate each other). Present the merged checklist to the user in **one block before testing** — this is the contract you're about to verify, and it's their chance to correct or trim it.

## Step 2 — Find the testable links

Find the preview/deploy URL the same way `gbase:monitor` does — you're opening it instead of just surfacing it.

- **Look in**: PR conversation/bot comments and CI checks — `gh pr view <pr> --json statusCheckRollup` for check `detailsUrl`s, `gh pr view <pr> --comments` for bot-posted links.
- **Targets**: preview / deploy / staging / review-app / Storybook / Chromatic / demo URLs. Skip docs, coverage badges, CI log pages, and issue/commit references.
- **Pick** the newest preview built from the PR head SHA (`headRefOid`); preview bots edit one comment per push, so take the current URL. Note the source (which bot/check) and the SHA you're testing.
- **If none found**: ask the user for the URL — they may run it locally (`localhost:3000`) or have a link the bot didn't post.

## Step 3 — Drive and verify in Claude-in-Chrome

`tabs_context_mcp` → `tabs_create_mcp` → `navigate` to the preview. If a login wall appears, follow the credentials safety rule (pause, ask the user to log in manually). Then work the checklist:

- **`[behavior]` items** — navigate to the relevant screen, perform the interaction (`find` the element → `computer` click/type), and observe the result. Capture a screenshot as evidence. Check `read_console_messages` with `onlyErrors: true` for runtime errors that a happy-path click might hide.
- **`[design]` items** — screenshot the component, then compare against the Figma reference from Step 1: layout, spacing, color tokens, typography, copy, and interactive states (hover/focus/disabled/empty/error). Pull `get_variable_defs` when a precise token (exact hex, spacing value) is worth checking rather than eyeballing.
- **Record each item** as `PASS` / `FAIL` / `BLOCKED` (login or missing screen) / `N/A` (can't verify from the UI), each with an evidence screenshot and a one-line note. Consider recording the run as a GIF (`gif_creator`) when the user will want to replay a multi-step flow.

## Step 4 — Report to the user

Produce a markdown report **to the user — never to the PR**:

- **Header**: PR title + number + URL, the preview URL, and the commit SHA tested.
- **Results table**: `# | requirement | type | source | result | evidence`.
- **Screenshots**: surface the evidence via `SendUserFile` so the user can see what you saw.
- **Summary**: `X/Y passed`. List every `FAIL` and `BLOCKED` with concrete repro steps, and for failures point at the likely-responsible `file:line` from the diff.
- **No GitHub side effects.** If the user then wants this posted as a PR comment, that's a separate explicit request — confirm before posting.

## Ambiguity → ask

Use `AskUserQuestion` (one decision per question, 2–3 concrete options) when:

- Multiple preview URLs exist and it's unclear which to test.
- A requirement is too vague to verify from the UI ("make it feel snappier").
- A behavior check can only be done by performing a real write/irreversible action.
- A login or environment access is required.
- A Figma link points at a whole file rather than a specific frame/node.

When in doubt, ask — a wrong assumption wastes a whole browser run.

## Error handling

- `gh` auth missing → stop, ask the user to run `gh auth login`.
- PR not found / not resolvable → stop, show exactly what was tried (the ref, the repo).
- No preview link discoverable → ask the user for a URL (local or otherwise).
- Browser extension unresponsive or tab invalid → re-run `tabs_context_mcp` for fresh IDs; after 2–3 failed attempts, stop and surface.
- Figma MCP not connected → fall back to any Figma screenshot the author pasted into the PR, or ask the user to share the design; don't block the behavior checks on it.

## Usage

```
/gbase:pr-verify <pr-url-or-number>
```

Typical session:

```
User: /gbase:pr-verify 142

Claude: PR #142 "feat: redesign profile settings card" — head 9a3f1c2.
Requirements I'll verify (from PR body + Figma + the diff):
  1. [behavior] Toggling "Public profile" persists after reload — PR body
  2. [behavior] Empty bio shows the new placeholder copy — diff (ProfileCard.tsx)
  3. [design]   Card matches Figma node 1:204 — spacing, radius, color tokens — Figma link
  4. [design]   Save button uses the new --accent token — Figma variables

Preview: https://app-git-fix-142.vercel.app (Vercel, built from 9a3f1c2). Opening it…
[login wall] This preview needs a daangn SSO login — can you sign in in the Chrome window I opened? I'll continue once you're in.

User: done

Claude: [drives each item, screenshots evidence]
Result: 3/4 passed.
  ✅ 1, 2, 4
  ❌ 3 [design] — card radius is 8px, Figma specifies 12px (ProfileCard.tsx:41, `rounded-lg`). Screenshot attached.
```
