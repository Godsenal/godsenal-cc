---
name: instagram-card-news
description: >-
  Makes Korean Instagram card news (carousel posts) for an information account — account name, bio, cards,
  and caption — from high-performing Korean card-news references opened first, in one fixed format template
  (same cover layout, slide split, type sizes, colors, slide count, and slide roles every post) with real
  captures and charts, and the sea-otter mascot only as the profile photo, never on a slide. Use when asked
  for 카드뉴스, an Instagram carousel, or an Instagram info account's name, bio, profile image, or post, or
  when the user gives feedback on one.
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
- **No useless caption lines, no image-less text cards** — 2026-10-27 "쓸데없는 캡션이랑 출처, 이미지는 하나도없음": each card carries a real visual — an actual tweet capture, a screen capture, or a chart. No source card or credit line either (content-common's no-sources rule, 2026-10-29); the tweet captures themselves stay.
- **Last card — no fixed CTA box** — 2026-10-29 (user decision 17:50, "CTA는 내용에 맞는 한 줄로 매번 바꿔"): never put the same closing box on every carousel (❤️ 좋아요 · 🔖 저장 · 💬 공유 · 👉 팔로우). The same ending line every time reads as a bot signal.
- **End on a follow ask, with this post's reason** — 2026-10-29 22:53 "이 글 마지막 두개처럼 팔로우 유도하는건 어떰? … 컨텐츠별로 다를거같은데 … 팔로우하면 요 ai 상용화 될때 알려준다던지": the carousel ends with two follow slides (layout in the template below; the reference's last two slides, as actually seen, are in [references/format-refs-2026-10-29.md](references/format-refs-2026-10-29.md#마지막-2장--팔로우-유도-dakuaaqergd)). The reason to follow is not a fixed card: write it for that post in one line, from what the post leaves open. Not public yet → "풀리면 바로 알려드릴게요"; price or date still unknown → "정해지면 바로 정리해 드릴게요"; a tip → the next step of the same tip. Never the same line twice in a row, never a generic "AI 소식을 가장 빠르게". Only promise what a follow can deliver: a new post on our feed. No "댓글 달면 보내드려요", no DM, no 알림 설정 promise ([content-common](../content-common/SKILL.md) bans comment→DM in every piece of content).
- **Mascot — profile photo only** — 2026-10-29 21:37 "무슨 캐릭터만들어서 카드뉴스만들고 이런게아님 그냥 형식만 잘 통일해서 잘만드는느낌": the sea otter (해달) the user picked on 2026-10-28 is the profile photo and nothing else. It goes on no slide, cover, or last card; what makes the account look made with care is the fixed format below. No name, never narrates ([content-common](../content-common/SKILL.md)'s no-mascot-voice rule). This replaces the older "mascot on every card" rule.

## Format template (@haedollar)

Same 2026-10-29 21:37 feedback. The two references the user named, @moodmode.ai and @ai.trend.kr, change only the cover image, the headline, and the captures from post to post; position, size, color, slide count, and each slide's role stay fixed (21 carousels opened, analysis and URLs in [references/format-refs-2026-10-29.md](references/format-refs-2026-10-29.md)). Every @haedollar carousel uses this one template. Change a value only with the user, then change it here, not per post.

| | Spec (1080×1440 px, 3:4) |
|---|---|
| Type | One family, Pretendard. Headlines ExtraBold with tight tracking; body Medium |
| Colors | Panel `#0B0B0B`, headline `#FFFFFF`, body `#B8B8B8`, one accent `#F5B82E` used in one place per slide at most |
| Margins | 72 px left and right on every slide; text left-aligned |
| Cover (1 slide) | Full-bleed image: a real screen or product photo, never the otter. Bottom 40% dark gradient. Bottom-left: tag pill `AI 뉴스` · `AI 팁` · `AI 돈` (26 px, only these three), then a 2-line headline at 88–96 px, ≤14자 per line, from [hook-templates](../hook-templates/SKILL.md) |
| Body slides (4–8) | Top 55%: one capture (tweet, screen, chart), edge to edge. Bottom 45%: `#0B0B0B` panel with the slide number (1, 2 …, 26 px), one headline line ≤16자 at 64 px, then ≤3 body lines at 34 px in 해요체; one bold phrase at most. No credit, `@handle`, or "출처" text on the slide; a capture keeps whatever is inside it |
| Follow slide 1 — this post's reason | The cover image blurred (24 px) at 40% brightness. One white box centered (radius 24, 72 px side margin), 3 lines centered at 52 px ExtraBold `#0B0B0B`: what is still open in this post + `→` / what the reader will get, on an accent `#F5B82E` marker / "바로 알려드릴게요"-style promise. Written for this post every time |
| Follow slide 2 — follow card | The cover image at 35% brightness, three blocks centered. Top: a small white label box with one question tied to this post (40 px). Middle: a white pill (radius 999) with the display name `해달러 \| 쉽게 푸는 AI 경제` (40 px), `@haedollar` in grey under it, and an accent `팔로우` button on the right; no profile photo (no otter on slides). Bottom: 2 white lines at 48 px saying what following gets them this time, one phrase in accent. No ♥💬🔖 icons, no "댓글 남기면" or DM line |
| Count and order | Cover → numbered body slides (4–7) → follow slide 1 → follow slide 2: 7–10 slides. A weekly roundup uses the same cover with the tag `AI 뉴스` and a second line "N월 N주 AI 소식"; how often it runs is the user's call |
| Caption | The Caption rules below; the first line restates the cover headline as a sentence. No English translation block, no `Editor`/`Created by`/`Source` lines (both references do these; we don't) |

Before handing off, put the cover, one body slide, and the two follow slides of the new carousel next to the previous post's and check that only the image, words, and captures differ, and that the follow reason is not the previous post's; write `format-check: 비율 3:4 | 장 N | 태그 <AI 뉴스> | 본문 제목 최대 N자 | 마스코트 0 | 팔로우 이유 "<한 줄>"` in the report.

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
- **Ending** — one CTA line written for that post, never the same line twice in a row (the last-card rule above applies to the caption too); it says the same follow reason as the follow slides, in other words. No DM promise (19 of 57 references used one; banned in [content-common](../content-common/SKILL.md)).
- **No credits, no mascot voice** — no "출처" or "📷 ○○" line (12 of 57 references had one) and no 금동이 or third-person character lines ([content-common](../content-common/SKILL.md)).
- **Self-check** — count before handing off and put one line in the work report, e.g. `caption-check: 첫줄 24자 | 238자 11줄 | 이모지 2 | 태그 3 | 봇 신호 0`:

```bash
python3 -c 'import re,sys;t=open(sys.argv[1]).read();g=re.findall(r"#\S+",t);b=re.sub(r"#\S+","",t);L=[l.strip() for l in b.splitlines() if l.strip()];e=re.findall("[\U0001F000-\U0001FAFF☀-➿]",b);print("첫줄",len(L[0]),"자 |",len("".join(L)),"자",len(L),"줄 | 이모지",len(e),"| 태그",len(g))' caption.txt
```

## Threads summary

A Threads post that summarizes a carousel is a Threads post first: it follows [threads-voice](../threads-voice/SKILL.md) (root caps, voice, self-check), not the card copy. Pointing to the carousel goes in a reply, not the root.

## Posting

**Never post without the user's explicit OK for that post.** Show the cards and caption first. Under `AGENT_HEADLESS=1` nothing is posted; report it as pending the user's OK. Comments on the post, and comments we leave on other accounts' posts, follow [comment-guide](../comment-guide/SKILL.md). Accounts that follow us are followed back per [content-common](../content-common/SKILL.md)'s follow-back rule (skip impersonation/spam/bots, ≤5 per round, logged).
