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
- **Last card — no fixed CTA box** — 2026-10-29 (user decision 17:50, "CTA는 내용에 맞는 한 줄로 매번 바꿔"): never put the same closing box on every carousel (❤️ 좋아요 · 🔖 저장 · 💬 공유 · 👉 팔로우). Write one CTA line that fits that post's content, different each time; the same ending line every time reads as a bot signal.
- **Mascot**: chosen by the user from several samples side by side; on 2026-10-28 the user picked a sea otter (해달). A new character only after another side-by-side comparison. It is the account's face only: no name, and it never narrates (2026-10-29, [content-common](../content-common/SKILL.md)'s no-mascot-voice rule).

## Name, bio

- **Name** — 2026-10-27 "ai머니노트 이게 말이되니", "이름 좀 다른거참고해봐": follow the naming patterns of real Korean info brands (잼비, 경제여우, 어피티, 뉴닉 …). Never glue keywords together ("AI머니노트", "지혼자 돈소식"), and no "브리핑" ([content-common](../content-common/SKILL.md)'s rejected phrases).
- **Bio** — match the tone of the reference bios' original text; the sourcing route ("X에서 골라와요"), AI-sounding phrasing, and comment→DM promises are banned in every piece of content ([content-common](../content-common/SKILL.md)'s rejected phrases).
- **No made-up schedule** — 2026-10-28 "왜 주 4회임?": a posting count or time goes into the bio only after the user sets it ([content-common](../content-common/SKILL.md)'s `가정:` rule).

## Caption

2026-10-29 "ㅇㅇ ㄱ" (user go-ahead 18:22 to set caption voice and length). Numbers are from 57 feed posts of 10 reference accounts opened in ego-browser on 2026-10-28 (`refs_ig.md` active list); method, per-account table, and the top 14 with URLs are in [references/caption-refs-2026-10-29.md](references/caption-refs-2026-10-29.md).

| | Rule | Measured (median, p25–p75) |
|---|---|---|
| Voice | **해요체.** One "~입니다" line to land a claim is fine; no 반말 or 음슴체 | 해요체 32 / 합쇼 12 / 반말·음슴 6 of 57 (5 of the 6 반말 are 잼비's character voice and ant_chart memes) |
| First line | **30자 이하** — the only line the feed shows before "더 보기" | 29자 (19–32) |
| Body (hashtags out) | **150–450자**, aim ~250 | 245자 (165–433); posts above their account's median like count: 221 |
| Lines (non-empty) | **7–15줄**, short lines | 12 (7–15) |
| Emoji | **0–5**, none fixed (no 🦦 on every caption) | 3 (1–5); 12 of 57 had none |
| Hashtags | **0–5** | 4 (0–5); 18 of 57 had none |

- **Bot signals** — 2026-10-29 (user decision 17:34), same as [threads-voice](../threads-voice/SKILL.md)'s: no "(저장/공유)"-style tag at the head of the first line (8 of 57 references had one; we don't), no closing "여러분 ~? 👇" question. End on the take.
- **Ending** — one CTA line written for that post, never the same line twice in a row (the last-card rule above applies to the caption too); no DM promise (19 of 57 references used one; banned in [content-common](../content-common/SKILL.md)).
- **No credits, no mascot voice** — no "출처" or "📷 ○○" line (12 of 57 references had one) and no 금동이 or third-person character lines ([content-common](../content-common/SKILL.md)).
- **Self-check** — count before handing off and put one line in the work report, e.g. `caption-check: 첫줄 24자 | 238자 11줄 | 이모지 2 | 태그 3 | 봇 신호 0`:

```bash
python3 -c 'import re,sys;t=open(sys.argv[1]).read();g=re.findall(r"#\S+",t);b=re.sub(r"#\S+","",t);L=[l.strip() for l in b.splitlines() if l.strip()];e=re.findall("[\U0001F000-\U0001FAFF☀-➿]",b);print("첫줄",len(L[0]),"자 |",len("".join(L)),"자",len(L),"줄 | 이모지",len(e),"| 태그",len(g))' caption.txt
```

## Threads summary

A Threads post that summarizes a carousel is a Threads post first: it follows [threads-voice](../threads-voice/SKILL.md) (root caps, voice, self-check), not the card copy. Pointing to the carousel goes in a reply, not the root.

## Posting

**Never post without the user's explicit OK for that post.** Show the cards and caption first. Under `AGENT_HEADLESS=1` nothing is posted; report it as pending the user's OK. Comments on the post, and comments we leave on other accounts' posts, follow [comment-guide](../comment-guide/SKILL.md). Accounts that follow us are followed back per [content-common](../content-common/SKILL.md)'s follow-back rule (skip impersonation/spam/bots, ≤5 per round, logged).
