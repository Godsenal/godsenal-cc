---
name: instagram-card-news
description: >-
  Makes Korean Instagram card news (carousel posts) for an information account — account name, bio, cards,
  and caption — from high-performing Korean card-news references opened first, with real tweet captures,
  charts, and a mascot on every card. Use when asked for 카드뉴스, an Instagram carousel, or an Instagram
  info account's name, bio, mascot, or post, or when the user gives feedback on one.
---

# instagram-card-news

Rules from the user's feedback on 2026-10-27–28. All of [content-common](../content-common/SKILL.md) applies; changes go through its feedback intake. Account details (account name, handle, paths, schedule) are the caller's settings, not this skill's — e.g. a work folder like `$HOME/LTH/insta`.

## 출력 언어

사용자에게 보이는 텍스트(진행 보고, 샘플 비교 설명, 리포트)와 카드 산출물(계정 이름, 소개글, 카드 문구, 캡션)은 **한국어**로 쓴다. 따옴표 안 한국어는 사용자 피드백 원문 인용이므로 그대로 둔다. 코드·경로·명령어는 대상 레포의 관례를 따른다. 사용자가 다른 언어로 요청하면 그 언어를 따른다.

## References first

**No cards before you have actually opened references.** The first attempt was made after the Instagram page timed out, without seeing any reference, and the result was bad. Open several high-performing Korean card-news posts and info accounts (in a logged-in browser if Instagram walls them), save the captures and the original text of their cards, bios, and captions into the work folder, and build from those. If none can be opened, stop and report it.

## Cards

- **Cover, first card, and the caption's first line** start from [hook-templates](../hook-templates/SKILL.md) and follow its 머니알림 rules.
- **No forced cards** — 2026-10-27 "뜬금없는 2,30대 개억지 체크포인트": every card must follow from the story; no filler checklist or audience-targeting card bolted on.
- **No useless caption lines, no image-less text cards** — 2026-10-27 "쓸데없는 캡션이랑 출처, 이미지는 하나도없음": each card carries a real visual — an actual tweet capture, a chart, or the mascot. No source card or credit line either (content-common's no-sources rule, 2026-10-29); the tweet captures themselves stay.
- **Mascot**: chosen by the user from several samples side by side; on 2026-10-28 the user picked a sea otter (해달). A new character only after another side-by-side comparison. It is the account's face only: no name, and it never narrates (2026-10-29, [content-common](../content-common/SKILL.md)'s no-mascot-voice rule).

## Name, bio, caption

- **Name** — 2026-10-27 "ai머니노트 이게 말이되니", "이름 좀 다른거참고해봐": follow the naming patterns of real Korean info brands (잼비, 경제여우, 어피티, 뉴닉 …). Never glue keywords together ("AI머니노트", "지혼자 돈소식"), and no "브리핑" ([content-common](../content-common/SKILL.md)'s rejected phrases).
- **Bio** — match the tone of the reference bios' original text; the sourcing route ("X에서 골라와요"), AI-sounding phrasing, and comment→DM promises are banned in every piece of content ([content-common](../content-common/SKILL.md)'s rejected phrases).
- **Caption bot signals** — 2026-10-29 (user decision 17:34), same as [threads-voice](../threads-voice/SKILL.md)'s bot signals: no "(저장/공유)"-style tag at the head of the first line, and no closing "여러분 ~? 👇" question. End on the take.
- **No made-up schedule** — 2026-10-28 "왜 주 4회임?": a posting count or time goes into the bio only after the user sets it ([content-common](../content-common/SKILL.md)'s `가정:` rule).

## Threads summary

A Threads post that summarizes a carousel is a Threads post first: it follows [threads-voice](../threads-voice/SKILL.md) (root caps, voice, self-check), not the card copy. Pointing to the carousel goes in a reply, not the root.

## Posting

**Never post without the user's explicit OK for that post.** Show the cards and caption first. Under `AGENT_HEADLESS=1` nothing is posted; report it as pending the user's OK.
