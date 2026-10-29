---
name: instagram-card-news
description: >-
  Makes Korean Instagram card news (carousel posts) for an information account — account name, bio, cards,
  and caption — from high-performing Korean card-news references opened first, in one fixed format template
  (same cover layout, slide split, type sizes, colors, slide count, and slide roles every post) with real
  captures and charts (1–3 video slides with a bundled HyperFrames chart-motion template), one follow card at the end (a comment→DM reward slide before it only with a real
  resource), and the sea-otter mascot only as the profile photo, never on a slide. Use when asked for
  카드뉴스, an Instagram carousel, or an Instagram info account's name, bio, profile image, or post, or when
  the user gives feedback on one.
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
- **End on one follow card, with this post's reason** — 2026-10-29 22:53 "이 글 마지막 두개처럼 팔로우 유도하는건 어떰? … 컨텐츠별로 다를거같은데 … 팔로우하면 요 ai 상용화 될때 알려준다던지"; 2026-10-29 23:25 (user decision) the ending is one slide by default, not the earlier "follow reason slide + follow card" pair: the account name, a follow button, and one line written for this post (layout in the template below; the reference's last two slides, as actually seen, are in [references/format-refs-2026-10-29.md](references/format-refs-2026-10-29.md#마지막-2장--팔로우-유도-dakuaaqergd)). The reason to follow is not a fixed card: write it for that post in one line, from what the post leaves open. Not public yet → "풀리면 바로 알려드릴게요"; price or date still unknown → "정해지면 바로 정리해 드릴게요"; a tip → the next step of the same tip. Never the same line twice in a row, never a generic "AI 소식을 가장 빠르게". Only promise what a follow can deliver: a new post on our feed. No 알림 설정 promise, and no comment or DM line on the follow card.
- **Comment→DM reward slide** — 2026-10-29 23:25 (user decision, research in [references/comment-reward-research-2026-10-29.md](references/comment-reward-research-2026-10-29.md)): allowed only under [content-common](../content-common/SKILL.md)'s "Comment→DM only with a real resource" rule (published on the public library first, no follow or share condition). `AI 팁` posts get one by default (a copy-paste prompt pack or a setup guide); `AI 돈` posts only when there is something to calculate (a number table with a worked example); `AI 뉴스` posts only when the resource gives more than the carousel (a full comparison table, a price calculation). It goes right before the follow card, using the reference's 6th-slide layout (blurred preview of the actual resource + white box: action → what they get → "DM으로 보내드려요"). Without a resource that qualifies, there is no reward slide.
- **Mascot — profile photo only** — 2026-10-29 21:37 "무슨 캐릭터만들어서 카드뉴스만들고 이런게아님 그냥 형식만 잘 통일해서 잘만드는느낌": the sea otter (해달) the user picked on 2026-10-28 is the profile photo and nothing else. It goes on no slide, cover, or last card; what makes the account look made with care is the fixed format below. No name, never narrates ([content-common](../content-common/SKILL.md)'s no-mascot-voice rule). This replaces the older "mascot on every card" rule.

## Format template (@haedollar)

Same 2026-10-29 21:37 feedback. The two references the user named, @moodmode.ai and @ai.trend.kr, change only the cover image, the headline, and the captures from post to post; position, size, color, slide count, and each slide's role stay fixed (21 carousels opened, analysis and URLs in [references/format-refs-2026-10-29.md](references/format-refs-2026-10-29.md)). Every @haedollar carousel uses this one template. Change a value only with the user, then change it here, not per post.

| | Spec (1080×1440 px, 3:4) |
|---|---|
| Type | One family, Pretendard. Headlines ExtraBold with tight tracking; body Medium |
| Colors | Panel `#0B0B0B`, headline `#FFFFFF`, body `#B8B8B8`, one accent `#F5B82E` used in one place per slide at most |
| Margins | 72 px left and right on every slide; text left-aligned |
| Cover (1 slide) | Full-bleed image: a real screen or product photo, never the otter. Bottom 40% dark gradient. Bottom-left: tag pill `AI 뉴스` · `AI 팁` · `AI 돈` (26 px, only these three), then a 2-line headline at 88–96 px, ≤14자 per line, from [hook-templates](../hook-templates/SKILL.md) |
| Body slides (4–7) | Top 55%: one capture (tweet, screen, chart), edge to edge; on a video slide only this area moves (Video slides below). Bottom 45%: `#0B0B0B` panel with the slide number (1, 2 …, 26 px), one headline line ≤16자 at 64 px, then ≤3 body lines at 34 px in 해요체; one bold phrase at most. No credit, `@handle`, or "출처" text on the slide; a capture keeps whatever is inside it |
| Reward slide (optional) | Only under the reward rule above. A blurred (24 px) capture of the actual resource at 40% brightness. One white box centered (radius 24, 72 px side margin), 3 lines centered at 52 px ExtraBold `#0B0B0B`: "댓글에 '<키워드>' 남기시면 →" / what they get, word for word as the resource's contents, on an accent `#F5B82E` marker / "DM으로 보내드려요". No follow condition |
| Follow card (1 slide) | The cover image at 35% brightness, three blocks centered. Top: a small white label box with one question tied to this post (40 px). Middle: a white pill (radius 999) with the display name `해달러 \| 쉽게 푸는 AI 경제` (40 px), `@haedollar` in grey under it, and an accent `팔로우` button on the right; no profile photo (no otter on slides). Bottom: the one line written for this post (up to 2 white lines at 48 px), saying what following gets them this time, one phrase in accent. No ♥💬🔖 icons, no "댓글 남기면" or DM line (the reward, if any, is on the slide before) |
| Count and order | Cover → numbered body slides (4–7) → reward slide (if any) → follow card: 6–10 slides. A weekly roundup uses the same cover with the tag `AI 뉴스` and a second line "N월 N주 AI 소식"; how often it runs is the user's call |
| Caption | The Caption rules below; the first line restates the cover headline as a sentence. No English translation block, no `Editor`/`Created by`/`Source` lines (both references do these; we don't) |

Before handing off, put the cover, one body slide, the reward slide if any, and the follow card of the new carousel next to the previous post's and check that only the image, words, and captures differ, and that the follow reason is not the previous post's; write `format-check: 비율 3:4 | 장 N | 태그 <AI 뉴스> | 본문 제목 최대 N자 | 마스코트 0 | 영상 장 <없음 / 2·4장> | 보상 장 <없음 / 키워드> | 팔로우 이유 "<한 줄>"` in the report.

## Video slides

2026-10-30 user go-ahead ("ㄱㄱㄱ", 00:16) after the mixed-carousel research in [references/video-slide-research-2026-10-29.md](references/video-slide-research-2026-10-29.md): @moodmode.ai mixes video into half its carousels, keeping the panel still and moving only the media area.

- **Shape** — a video slide is a body slide whose top media area (1080×792, 55%) moves; the bottom panel is the photo slide's, unchanged and still for the whole clip. 1080×1440 H.264 30 fps yuv420p, no audio track, 3–15 s, and the final screen held **at least 4 s** (a paused or captured mid-count-up frame shows wrong numbers). Text inside the media area 28 px or more (delivered video can drop to 720×960); the panel keeps the photo spec, so HyperFrames' 26 px warning on the slide number is expected.
- **What moves** — `AI 팁`: a screen recording we made ourselves comes first. `AI 뉴스` and `AI 돈`: chart motion from the template below. Never someone else's launch video or demo clip: we can't credit it (no-sources rule), so it is a copyright risk.
- **Where** — 1–3 video slides among body slides 2–5. The cover stays a photo by default; the reward slide and follow card are always photos (all 32 reference mixed carousels end on photos).
- **Upload** — web upload only, all files in one go, then pick **원본** in the crop screen's ratio button (default 1:1 crops every slide, and the first slide's ratio applies to all). The API may reject or crop 3:4, so don't switch to it without testing. Leave generous upload waits once a video is in.
- **Effect not proven** — mixed carousels did not beat photo-only ones in the references (median likes 474 vs 577). For the first few carousels with video slides, log saves and likes next to comparable photo-only posts in the account's existing performance record (the work folder's insights log), and report the comparison; keep or drop video slides on that, not on taste.
- **Reels** — the video slides of one post can be joined into a 7–15 s reel of the same topic; making reels is out of scope here.

**Chart motion template** — [templates/chart-motion/](templates/chart-motion/) (HyperFrames pinned to `hyperframes@0.8.210`): `bar` (2–5 bars filling with count-up, then the highlighted one stays lit) and `compare` (two cards, e.g. two prices). Write one JSON with the data (`items[].label/value/highlight/note`, `prefix`/`suffix` unit (ASCII such as `$` or `%`, so OCR can check it; a Korean unit goes in `subcaption`), `decimals`, `max` for bars, `caption`/`subcaption`/`footnote`) and the panel (`num`, `title`, `body` lines with one `**bold**`); examples in `templates/chart-motion/examples/`. Use the same numbers as the still build, then:

```bash
python3 scripts/chart_motion.py slide.json -o out/03.mp4 [--fonts <Pretendard dir>]
```

It validates the JSON (title ≤16자, ≤3 body lines, values fit, hold ≥4 s), runs `hyperframes check` and `render`, checks the spec with ffprobe, saves start/mid/end frames next to the mp4, checks the last 4 s are still (SSIM), and OCRs each end-frame number against the input; any miss exits 1. Open the end frame next to the still slide before handing off and put its `chart-motion-check:` line in the report.

## Name, bio

- **Name** — 2026-10-27 "ai머니노트 이게 말이되니", "이름 좀 다른거참고해봐": follow the naming patterns of real Korean info brands (잼비, 경제여우, 어피티, 뉴닉 …). Never glue keywords together ("AI머니노트", "지혼자 돈소식"), and no "브리핑" ([content-common](../content-common/SKILL.md)'s rejected phrases).
- **Bio** — match the tone of the reference bios' original text; the sourcing route ("X에서 골라와요") and AI-sounding phrasing are banned in every piece of content ([content-common](../content-common/SKILL.md)'s rejected phrases). No comment→DM promise in the bio; a "DM 못 받으셨다면" link to the public library is fine.
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
- **Ending** — one CTA line written for that post, never the same line twice in a row (the last-card rule above applies to the caption too); it says the same follow reason as the follow card, in other words. One DM line only when the post has a reward slide; it names the keyword and the resource exactly as on the slide (19 of 57 references used a DM line; the conditions are [content-common](../content-common/SKILL.md)'s).
- **No credits, no mascot voice** — no "출처" or "📷 ○○" line (12 of 57 references had one) and no 금동이 or third-person character lines ([content-common](../content-common/SKILL.md)).
- **Self-check** — count before handing off and put one line in the work report, e.g. `caption-check: 첫줄 24자 | 238자 11줄 | 이모지 2 | 태그 3 | 봇 신호 0`:

```bash
python3 -c 'import re,sys;t=open(sys.argv[1]).read();g=re.findall(r"#\S+",t);b=re.sub(r"#\S+","",t);L=[l.strip() for l in b.splitlines() if l.strip()];e=re.findall("[\U0001F000-\U0001FAFF☀-➿]",b);print("첫줄",len(L[0]),"자 |",len("".join(L)),"자",len(L),"줄 | 이모지",len(e),"| 태그",len(g))' caption.txt
```

## Threads summary

A Threads post that summarizes a carousel is a Threads post first: it follows [threads-voice](../threads-voice/SKILL.md) (root caps, voice, self-check), not the card copy. Pointing to the carousel goes in a reply, not the root.

## Posting

**Never post without the user's explicit OK for that post.** Show the cards and caption first. Under `AGENT_HEADLESS=1` nothing is posted; report it as pending the user's OK. Comments on the post, and comments we leave on other accounts' posts, follow [comment-guide](../comment-guide/SKILL.md). Accounts that follow us are followed back per [content-common](../content-common/SKILL.md)'s follow-back rule (skip impersonation/spam/bots, ≤5 per round, logged).
