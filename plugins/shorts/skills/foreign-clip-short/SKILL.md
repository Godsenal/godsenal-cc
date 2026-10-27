---
name: foreign-clip-short
description: >-
  Makes a faceless Korean short from an official foreign show clip — Shark Tank, Dragons' Den, Shark Tank
  Australia pitches, Antiques Roadshow appraisals, Pawn Stars haggles, Kitchen Nightmares restaurants, and
  Undercover Boss reveals — in the user-approved framing D (black 9:16 canvas,
  fixed two-line title, center-cropped footage, Korean subtitles), with mostly original dialogue and 3–4
  narration bridges. Use when asked for a Shark Tank / Dragons' Den / Antiques Roadshow / Pawn Stars / Kitchen
  Nightmares / Undercover Boss / 샤크탱크 / 드래곤스덴 / 앤티크 로드쇼 / 전당포 사나이들 / 키친 나이트메어 / 언더커버 보스 short, reel, or TikTok, or any short built on a foreign TV clip with Korean subtitles.
---

# foreign-clip-short

Agreed with the user on 2026-10-25 after analyzing 12 popular Korean Shark Tank shorts and four rounds of feedback; Antiques Roadshow follows the same format. Applies on top of [shorts-common](../shorts-common/SKILL.md); changes go through its feedback intake.

## 출력 언어

사용자에게 보이는 텍스트(진행 보고, 리포트)와 영상 산출물(자막, 해설, 제목, 캡션)은 **한국어**로 쓴다. 따옴표 안 한국어는 사용자 피드백·합의 문구 인용이므로 그대로 둔다. 코드·경로·명령어는 대상 레포의 관례를 따른다. 사용자가 다른 언어로 요청하면 그 언어를 따른다.

## Source

- Official channel uploads only (Shark Tank Global/US, Dragons' Den, Shark Tank Australia, BBC/PBS Antiques Roadshow, `@PawnStars`, `@gordonramsay` / `@KitchenNightmares`, Undercover Boss …). Shows with an official Korean rights holder (Pawn Stars / 전당포 사나이들 → '히스토리', Undercover Boss) were excluded until 2026-10-26, when the user made 전당포 사나이들 a fixed series ("전당포 사나이들처럼 새 쇼는 … 쇼별 포맷 스펙"). Use them, skip items the Korean rights holder already posted, and note the claim risk in REPORT/FACTS.
- Pick episodes with a clear product or object, a fight between investors, a fast deal, or a twist ending / surprising price.
- Download into `out/<date>_<slug>/source/` (yt-dlp: best video up to 1080p + best audio). Save the source URL in REPORT.md.

## Structure

1. **Hook (0–5s)**: the most dramatic line or moment — for appraisals, the price or the owner's reaction.
2. **What it is (~17–25s)**: original pitch/demo, or the appraiser's explanation with close-ups. Viewers must understand the product or object.
3. **Back-and-forth**: offers, counters, sharks arguing — or the backstory and appraisal build-up.
4. **Result**: deal or no deal / the price reveal, and the reaction.

Original dialogue carries most of the video (~90%). Length and pacing rules are in shorts-common (45–55s, every silence over 0.15s cut).

## Redesign B — the default since 2026-10-26

The user picked B ("해외쇼쇼식", modeled on the most-viewed foreign-show clip shorts) out of four drafts (`$HOME/tiktok-share/2026-10-26/redesign/`). Build the plan with the pipeline's `scripts/clip/make_b.py` from a first-pass plan + word timestamps + a small spec (weak lines to `drop`, situation `tags`). The renderer default `PACE_B` does the rest:
- 1.08× speed (pitch kept); each footage piece alternates zoom 1.0/1.14/1.06/1.2, so every jump cut reads as a new angle (pieces under 0.6s keep the previous zoom).
- Big bold one-line subtitle at 60% of the footage height. On each line, one word (a number, a `*key*` word, or the longest word) is colored, cycling yellow → green → sky → red → pink; the rest is white with a thick black stroke.
- Small situation tag above the subtitle per scene (`*로리 vs 케빈*`, `*최종 결정*`, 2.2s). Tags name people from what's on screen, so check them against the source.
- **Next-episode end card** (series clips, from 2026-10-28 production; user picked draft A 교체·팝 on 2026-10-27): put `"stock": "<stock folder name>"` (`MMDD-HHMM_<series>-<NN>_<slug>`) in `plan.json` and the last 1.5s replaces the top headline with yellow text that pops 82%→100% in 0.25s — `다음 #3 · 내일 18:00` plus the next episode's queue `hook`, or `다음 회차도 곧 올라와요` when the next slot is unknown (same source as `scripts/series-cta.mjs`; preview with `--endcard`). Write the next episode's `stock`/`slot`/`hook` in `topics/clips/queue.json` before rendering. No narration or sfx is added. Never on narration videos or TOP3; never re-render a video already scheduled.
- Number subtitles get a hit SFX and a 4-frame color flash on the footage, aligned to the cut frame. No punch-in, no boundary whoosh.
- Framing D stays as below.

Appraisal variant (agent-built, ran as stock but not separately confirmed by the user): price hook → owner's story → appraiser explains the object (~18s) → price reveal + reaction. Add a KRW estimate line to foreign prices (the stock runs used about 1달러≈1,400원, 1파운드≈1,800원 — mark it as an estimate).

## Per-show variants (2026-10-26)

One fixed show per clip slot (pipeline `docs/SERIES.md`); the full spec for each is in the pipeline's `docs/formats/<show>.md`. What differs from the structure above:

| Show (slot) | Story spine | Title line 1 | Gotchas |
|---|---|---|---|
| 앤티크 로드쇼 (07:30) | owner's story → expert → price reveal (hook reuses it) | `<cheap price> <object>` | appraisal price card at the very end — stop the clip before it |
| 전당포 사나이들 (18:00) | asking price → expert valuation → 3–5 haggling turns → deal or walk-out | `<원화> 부른 <물건>` | burned-in price tags (`was/now/still $…`), name bars, red fact boxes at 70% height → `crop: 0.68–0.78` or `video` close-ups; end card in the last 7–10s |
| 샤크탱크 / 드래곤스 덴 (21:00) | as above | number / result | offer bars → `crop: 0.78` |
| 키친 나이트메어 (23:00) | the restaurant's money trouble first (debt, monthly loss, mortgaged home), then Ramsay's tasting or fridge check, then his verdict | money trouble: `집까지 담보 잡힌 피자집` | full 40–45 min episodes, not multi-restaurant compilations; name bars; translate meaning, not swearing; first cut came out 39.9s — use 3–4 problem scenes |
| 언더커버 보스 (spare for 07:30) | one employee's hardship → boss reveal → the biggest gift | the gift in 원화 | dissolve transitions make 1-frame flicker — end clips before them; crying lines fall under make_b's voice threshold (check by chunked transcription); hook footage via `video` on the crying face |

Narration stays at 3–4 lines in every variant (2026-10-26 "해설 양은 지금 그대로").

## Subtitles

- Accurate Korean subtitles, mostly the original dialogue translated. Transcribe with at least Whisper small (`faster-whisper small.en`, cross-checked with `medium.en`; word timings: pipeline `scripts/pace-test/words.py`). Check **who says each line**, especially offers, and that every amount matches the original.
- Subtitle style (lines ≤14 chars, B colors above) lives in the pipeline's `docs/CLIP.md`; subtitles go in `plan.json` `clip.subs`.

## Framing D (reference: youtube.com/shorts/YJ93QlV37-I)

- Black 1080×1920 canvas.
- Fixed two-line title in the top black area, y ≈ 250–470: line 1 yellow, line 2 white, bold with a black stroke; inside the profile-grid safe area.
- Footage center-cropped to about 1080×930 (~65% of the 16:9 width) at y ≈ 485. **Not** a full-frame 9:16 crop — the user found it too zoomed in.
- Subtitles inside the footage at 60% of its height (B).
- Cover: same style with the title (the frame at ~0.6s, showing the title and the product).
- Pipeline: `frame: box` (default) in `plan.json`; per-cut focus `x` (0–1); a numeric `crop` (<1) hides burned-in name bars. Details in `docs/SHARK_TANK.md`.

## Narration examples (tone rules are in shorts-common)

- Hook: "샤크탱크 역사상 가장 빠른 딜이었다는데", "21살 발명품에 샤크들이 싸웠다는데", "잡초 뽑다 주운 돌을 30년이나 갖고 있었다는데".
- Middle: "그때 샤크들이 투자를 제안하는데", "감정사가 한참 들여다보는데" (ding).
- Before the decision: "그리고 가격을 듣더니" (hit).

## Format-specific checks

On top of shorts-common's checks and the subtitle checks above: the title's claim matches what the clip shows; the footage area has no black bars from the crop; situation tags name the right person; `listen_check.py` hears the kept original words (compare its share with the un-cut version — Whisper misses a few words at hard-cut starts either way).
