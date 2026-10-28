---
name: content-common
description: >-
  Holds the user-confirmed rules for every piece of content the gshorts harness makes — shorts, Instagram
  card news, and any account name, bio, caption, script, or post copy — chiefly that Claude Code writes it from
  high-performing references it actually opened on the target platform (X, Instagram, YouTube), and that every
  mistake or lesson is written into this plugin the same turn so other bots don't repeat it. Also holds
  orchestrator operations notes. Use before naming an account, writing a bio, caption, card, or script, when
  the user gives feedback that applies across formats, or when a gshorts skill points here.
---

# content-common — rules for every piece of content

Applies to everything gshorts makes. Video-wide rules live in [shorts-common](../shorts-common/SKILL.md), Instagram card news in [instagram-card-news](../instagram-card-news/SKILL.md); both point here. When they disagree, the newer dated feedback wins.

## 출력 언어

사용자에게 보이는 텍스트(진행 보고, 샘플 비교 설명, 리포트)와 콘텐츠 산출물(이름, 소개글, 캡션, 카드 문구, 대본)은 **한국어**로 쓴다. 따옴표 안 한국어는 사용자 피드백 원문 인용이므로 번역하지 않는다. 코드·경로·명령어·환경변수 이름과 커밋 메시지는 대상 레포의 관례를 따른다. 사용자가 다른 언어로 요청하면 그 언어를 따른다.

## Rules for every piece of content (user-confirmed)

Quotes are the user's words with the date they were said.

- **Written by Claude Code from real references** — 2026-10-28 "항상 이런 컨텐츠 관련은 x나 인스타 유튜브등 적절한 플랫폼에 있는 잘나가는 레퍼런스를 기반으로 클로드코드가 참고해서 쓰는걸로해": every content judgment and every line of copy — names, bios, captions, card news, scripts — is done by Claude Code, not made up by the orchestrator bot on its own. First open references that actually perform well on that platform (X, Instagram, YouTube, whichever the content is for), collect their original text, then write from it. Note the references (URL + the quoted original) in the work folder's report. If the references can't be opened (timeout, login wall), stop and say so; don't write from memory.
- **Mistakes are recorded the same turn** — 2026-10-28 "똑같은 실수가 여러봇들에서 반복되지않게": several bots run this harness, so a mistake one makes or a lesson one learns is written into this plugin within that turn, at the place the feedback intake below points to — never only in a chat reply or a bot's own memory.

## Feedback intake — same turn, every time

Every new piece of user feedback or lesson is written into a skill **before** continuing the work:

1. Classify it: every piece of content → this file's rules; every video → shorts-common's "Rules for every video"; one format → that format skill (`foreign-clip-short`, `top3-compilation-short`, `instagram-card-news`); a new format → a new `skills/<format>/SKILL.md` that points here (and at shorts-common if it's a video); how the orchestrator runs the work → "Operations notes" below.
2. Write it as a rule with the date and the user's own words in quotes (`2026-10-28 "지금 좀 ai같은데": …`). If it contradicts an existing rule, rewrite that rule with the new date instead of adding a second one.
3. Then update the pipeline or tooling default it implies, if any.

Edit the gshorts source in the godsenal-cc checkout (`plugins/shorts/skills/…`; on the reference machine `$HOME/LTH/godsenal-cc`), not the installed plugin cache — the cache is overwritten on update. Bump the gshorts version in both `plugins/shorts/.claude-plugin/plugin.json` and `.claude-plugin/marketplace.json` (patch for a rule, minor for a new format skill); installed copies only change once it ships.

## Operations notes (orchestrator)

- **Background jobs on the Mac mini don't report back** (2026-10-28): a job started in the background there sends the bot no completion notice when it ends. Wait for it in the foreground, or check its output again yourself before reporting it done; never assume it finished.
